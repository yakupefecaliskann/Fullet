import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/news_item.dart';
import '../models/station.dart';
import '../models/map_focus_mode.dart';
import '../services/analytics_service.dart';
import '../services/supabase_service.dart';
import '../services/smart_station_service.dart';
import '../providers/user_preferences_provider.dart';
import '../widgets/garage_modal.dart';
import '../widgets/station_bottom_sheet.dart';
import '../widgets/ful_side_menu.dart';
import '../widgets/settings_sheet.dart';
import '../widgets/price_alert_dialog.dart';
import '../services/price_alert_service.dart';
import '../services/savings_service.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../utils/price_formatter.dart';
import '../utils/marker_icon_factory.dart';
import '../utils/distance_calculator.dart';
import '../utils/brand_utils.dart';
import '../widgets/top_search_bar.dart';
import '../theme/ful_theme.dart';
import '../services/notification_service.dart';
import '../services/auth_service.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ModernMapScreen extends StatefulWidget {
  final bool openGarageOnStart;

  const ModernMapScreen({
    super.key,
    this.openGarageOnStart = false,
  });

  @override
  State<ModernMapScreen> createState() => _ModernMapScreenState();
}

enum _LocationState { checking, precise, fallback, serviceOff, denied }

class _ModernMapScreenState extends State<ModernMapScreen> {
  static const double _drivingFetchRadiusMeters = 30000;
  static const double _drivingFetchMoveMeters = 1200;
  static const Duration _drivingFetchInterval = Duration(seconds: 45);
  GoogleMapController? _mapController;
  LatLng _currentLocation =
      const LatLng(41.0082, 28.9784); // Default to Istanbul immediately
  List<Station> _stations = [];
  List<NewsItem> _news = [];
  bool _isLoading = true;
  bool _isFetchingStations = false;
  String? _stationLoadError;
  _LocationState _locationState = _LocationState.checking;

  Station? _visibleStation;
  SmartStationResult? _smartResult;
  String? _nearestStationId;
  final ValueNotifier<Set<Marker>> _markersNotifier = ValueNotifier({});
  double _currentZoom = 12;
  Set<String> _selectedBrands = {};
  MapFocusMode _focusMode = MapFocusMode.smart;

  User? _currentUser;
  StreamSubscription<User?>? _authSubscription;

  Timer? _fetchDebouncer;
  Timer? _markerDebouncer;
  StreamSubscription<Position>? _drivingPositionSubscription;
  int _stationFetchSerial = 0;
  int _markerBuildSerial = 0;
  int? _renderedZoomBucket;
  LatLng? _lastFetchCenter;
  double? _lastFetchRadiusMeters;
  bool _drivingModeEnabled = false;
  bool _isStartingDrivingMode = false;
  String? _drivingError;
  LatLng? _lastDrivingFetchLocation;
  DateTime? _lastDrivingFetchAt;
  bool? _isDarkModeOverride;

  bool get _currentIsDark {
    if (_isDarkModeOverride != null) return _isDarkModeOverride!;
    return WidgetsBinding.instance.platformDispatcher.platformBrightness ==
        Brightness.dark;
  }

  bool _menuOpen = false;

  @override
  void initState() {
    super.initState();
    _currentUser = AuthService.currentUser;
    if (_currentUser != null) {
      unawaited(_handleSignIn(_currentUser!));
    }
    _authSubscription = AuthService.authStateChanges.listen((user) {
      if (!mounted) return;
      final prev = _currentUser;
      setState(() => _currentUser = user);
      if (user != null && prev == null) {
        unawaited(_handleSignIn(user));
      }
    });
    if (widget.openGarageOnStart) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        _openGarage();
      });
    }
    WidgetsBinding.instance.addPostFrameCallback((_) => _initData());
  }

  Future<void> _initData() async {
    await _getLocation();
    unawaited(_requestNotificationsOnce());
    unawaited(NotificationService.ensureFuelReminderScheduled());
    unawaited(_loadNews());
    await _fetchStationsForRegion(_currentLocation);
    if (!mounted) return;
    setState(() => _isLoading = false);
    unawaited(SupabaseService.fetchAllActiveStationsSafe());
    unawaited(_checkPriceAlerts());
  }

  Future<void> _checkPriceAlerts() async {
    final uid = _currentUser?.uid;
    if (uid == null) return;
    final stations = await SupabaseService.fetchAllActiveStationsSafe();
    await PriceAlertService.checkAlerts(uid, stations);
  }

  Future<void> _onSignInTapped() async {
    final result = await AuthService.signInWithGoogle();
    if (!mounted) return;
    if (result.isSuccess) {
      setState(() => _menuOpen = false);
      return;
    }
    if (result.status != AuthResultStatus.error) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(result.message ?? 'Giriş yapılamadı, tekrar dene.'),
      ),
    );
  }

  Future<void> _handleSignIn(User user) async {
    await AuthService.ensureAuthenticatedRole(user);
    // fullet_favorites.firebase_uid, fullet_users(firebase_uid)'a FK ile
    // bağlı — favori senkronizasyonundan önce profil satırının var
    // olduğundan emin olunmalı (yalnızca signInWithGoogle()'da değil,
    // kalıcı oturumla soğuk başlatmada da).
    await SupabaseService.upsertUserProfile(
      uid: user.uid,
      displayName: user.displayName,
      email: user.email,
      avatarUrl: user.photoURL,
    );
    if (!mounted) return;
    final prefs = context.read<UserPreferencesProvider>();
    await prefs.ready;
    if (!mounted) return;
    final localFavorites = prefs.favoriteStationIds;
    if (localFavorites.isNotEmpty) {
      await SupabaseService.syncLocalFavorites(user.uid, localFavorites);
    }
    final remoteFavorites = await SupabaseService.getUserFavorites(user.uid);
    if (remoteFavorites.isNotEmpty && mounted) {
      await prefs.mergeRemoteFavorites(remoteFavorites);
    }
  }

  Future<void> _requestNotificationsOnce() async {
    final prefs = await SharedPreferences.getInstance();
    if (prefs.getBool('notifications_initialized') == true) return;
    // Bayrağı hemen set et — izin verilse de verilmese de bir daha sorma
    await prefs.setBool('notifications_initialized', true);
    try {
      final granted = await NotificationService.requestPermission();
      if (!granted) return;
      await NotificationService.ensureFuelReminderScheduled();
      await NotificationService.scheduleGarageReminder();
    } catch (_) {}
  }

  Future<void> _loadNews() async {
    final news = await SupabaseService.fetchNews();
    if (!mounted) return;
    setState(() => _news = news);
  }

  Future<void> _getLocation() async {
    final permissionGranted = await _ensureLocationPermission();
    if (!permissionGranted) {
      if (_locationState == _LocationState.checking) {
        _setDefaultLocation(_LocationState.denied);
      }
      return;
    }

    // Kademe 1: Medium accuracy — hem GPS hem network kullanır, daha hızlı
    try {
      final position = await Geolocator.getCurrentPosition(
              desiredAccuracy: LocationAccuracy.medium)
          .timeout(const Duration(seconds: 5));
      final location = _locationFromPosition(position);
      if (location != null) {
        if (!mounted) return;
        setState(() {
          _currentLocation = location;
          _locationState = _LocationState.precise;
        });
        _mapController?.animateCamera(
          CameraUpdate.newCameraPosition(
            CameraPosition(target: location, zoom: 13),
          ),
        );
        return;
      }
    } catch (_) {}

    // Kademe 2: Low accuracy — son bilinen konum dahil
    try {
      final position = await Geolocator.getCurrentPosition(
              desiredAccuracy: LocationAccuracy.low)
          .timeout(const Duration(seconds: 4));
      final location = _locationFromPosition(position);
      if (location != null) {
        if (!mounted) return;
        setState(() {
          _currentLocation = location;
          _locationState = _LocationState.fallback;
        });
        _mapController?.animateCamera(
          CameraUpdate.newCameraPosition(
            CameraPosition(target: location, zoom: 12),
          ),
        );
        return;
      }
    } catch (_) {}

    // Kademe 3: Son bilinen konum
    try {
      final lastKnown = await Geolocator.getLastKnownPosition();
      if (lastKnown != null) {
        final location = _locationFromPosition(lastKnown);
        if (location != null) {
          if (!mounted) return;
          setState(() {
            _currentLocation = location;
            _locationState = _LocationState.fallback;
          });
          _mapController?.animateCamera(
            CameraUpdate.newCameraPosition(
              CameraPosition(target: location, zoom: 12),
            ),
          );
          return;
        }
      }
    } catch (_) {}

    // Kademe 4: Türkiye genel görünümü (pes etme, harita kullanılabilir olsun)
    if (!mounted) return;
    setState(() {
      _currentLocation = const LatLng(39.0, 35.0); // Türkiye merkezi
      _locationState = _LocationState.fallback;
    });
    _mapController?.animateCamera(
      CameraUpdate.newCameraPosition(
        const CameraPosition(target: LatLng(39.0, 35.0), zoom: 6.2),
      ),
    );
  }

  Future<bool> _ensureLocationPermission() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      _setDefaultLocation(_LocationState.serviceOff);
      return false;
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        _setDefaultLocation(_LocationState.denied);
        return false;
      }
    }

    if (permission == LocationPermission.deniedForever) {
      _setDefaultLocation(_LocationState.denied);
      return false;
    }

    return true;
  }

  LatLng? _locationFromPosition(Position position) {
    // Türkiye sınırları içinde mi kontrol et
    if (position.latitude < 35.5 ||
        position.latitude > 42.5 ||
        position.longitude < 25.5 ||
        position.longitude > 45.0) {
      return null;
    }
    // Doğruluk çok kötüyse (>5km) yine de kabul et — GPS yoksa network yeter
    return LatLng(position.latitude, position.longitude);
  }

  void _setDefaultLocation(_LocationState state) {
    if (!mounted) return;
    // Konum reddedildiyse Türkiye genel görünümünü göster
    setState(() {
      _locationState = state;
      if (state == _LocationState.denied ||
          state == _LocationState.serviceOff) {
        _currentLocation = const LatLng(39.0, 35.0);
      }
    });
  }

  Future<void> _fetchStationsForRegion(
    LatLng center, {
    double maxDistMeters = 20000,
    int? maxResults,
    Set<String>? brandKeys,
  }) async {
    final requestId = ++_stationFetchSerial;
    final selectedBrandKeys = brandKeys ?? _selectedBrands;
    if (mounted && !_isLoading) {
      setState(() => _isFetchingStations = true);
    }
    final data = await SupabaseService.fetchStations(
      latitude: center.latitude,
      longitude: center.longitude,
      maxDistMeters: maxDistMeters,
      maxResults: maxResults ?? _maxResultsForZoom(_currentZoom),
      brandKeys: selectedBrandKeys,
    );
    if (!mounted || requestId != _stationFetchSerial) return;
    setState(() {
      _stations = data;
      _lastFetchCenter = center;
      _lastFetchRadiusMeters = maxDistMeters;
      _stationLoadError = SupabaseService.lastStationFetchError;
      _isFetchingStations = false;
    });
    _updateCalculationsAndMarkers(forceMarkerRefresh: true);
  }

  void _updateCalculationsAndMarkers({bool forceMarkerRefresh = false}) {
    if (!mounted) return;
    final prefs = context.read<UserPreferencesProvider>();
    final displayStations = _filteredStations(fuelType: prefs.selectedFuel);

    _smartResult = SmartStationService.calculateBestStations(
      location: _currentLocation,
      stations: displayStations,
      selectedFuel: prefs.selectedFuel,
      tankCapacity: prefs.tankCapacity,
      fuelConsumption: prefs.fuelConsumption,
    );
    _nearestStationId = _nearestStationIdFor(displayStations);

    _scheduleMarkerRefresh(force: forceMarkerRefresh);
  }

  List<Station> _filteredStations({required String fuelType}) {
    final result = _stationsWithFuel(fuelType).where((station) {
      if (_selectedBrands.isNotEmpty &&
          !_selectedBrands.contains(canonicalBrandKey(station.brand))) {
        return false;
      }
      return true;
    }).toList(growable: false);
    return result;
  }

  List<Station> _stationsWithFuel(String fuelType) {
    final result = _stations
        .where((station) =>
            station.hasDisplayablePriceFor(fuelType) || station.isVisibleInApp)
        .toList(growable: false);
    return result;
  }

  String? _nearestStationIdFor(List<Station> stations) {
    String? nearestId;
    double bestDistance = double.infinity;
    for (final station in stations) {
      final distance = getDistanceKm(
        _currentLocation.latitude,
        _currentLocation.longitude,
        station.latitude,
        station.longitude,
      );
      if (distance == null || distance >= bestDistance) continue;
      bestDistance = distance;
      nearestId = station.id;
    }
    return nearestId;
  }

  Station? _nearestStationFor(List<Station> stations) {
    Station? nearest;
    double bestDistance = double.infinity;
    for (final station in stations) {
      final distance = getDistanceKm(
        _currentLocation.latitude,
        _currentLocation.longitude,
        station.latitude,
        station.longitude,
      );
      if (distance == null || distance >= bestDistance) continue;
      bestDistance = distance;
      nearest = station;
    }
    return nearest;
  }

  Station? _drivingTargetStation(String fuelType) {
    return _nearestStationFor(_stationsWithFuel(fuelType));
  }

  double? _distanceToStation(Station? station) {
    if (station == null) return null;
    return getDistanceKm(
      _currentLocation.latitude,
      _currentLocation.longitude,
      station.latitude,
      station.longitude,
    );
  }

  Future<void> _toggleDrivingMode() async {
    if (_drivingModeEnabled) {
      _stopDrivingMode();
      return;
    }
    await _startDrivingMode();
  }

  Future<void> _startDrivingMode() async {
    if (_isStartingDrivingMode) return;
    setState(() {
      _isStartingDrivingMode = true;
      _drivingError = null;
    });

    final permissionGranted = await _ensureLocationPermission();
    if (!mounted) return;
    if (!permissionGranted) {
      setState(() {
        _isStartingDrivingMode = false;
        _drivingError = 'Konum izni olmadan sürüş takibi açılamaz.';
      });
      return;
    }

    try {
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      ).timeout(const Duration(seconds: 6));
      final location = _locationFromPosition(position);
      if (!mounted) return;
      if (location == null) {
        setState(() {
          _isStartingDrivingMode = false;
          _drivingError = 'Geçerli Türkiye konumu alınamadı.';
        });
        return;
      }

      setState(() {
        _currentLocation = location;
        _locationState = _LocationState.precise;
        _drivingModeEnabled = true;
        _isStartingDrivingMode = false;
        _lastDrivingFetchLocation = location;
        _lastDrivingFetchAt = DateTime.now();
      });
      _updateCalculationsAndMarkers(forceMarkerRefresh: true);
      unawaited(_fetchStationsForRegion(
        location,
        maxDistMeters: _drivingFetchRadiusMeters,
        maxResults: 300,
      ));
      _followDrivingCamera(location);
      _listenToDrivingPosition();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isStartingDrivingMode = false;
        _drivingError = 'Canlı konum başlatılamadı.';
      });
    }
  }

  void _listenToDrivingPosition() {
    _drivingPositionSubscription?.cancel();
    const locationSettings = LocationSettings(
      accuracy: LocationAccuracy.high,
      distanceFilter: 100,
    );
    _drivingPositionSubscription = Geolocator.getPositionStream(
      locationSettings: locationSettings,
    ).listen(
      _handleDrivingPosition,
      onError: (_) {
        if (!mounted) return;
        setState(() {
          _drivingError = 'Canlı konum geçici olarak alınamıyor.';
        });
      },
    );
  }

  void _handleDrivingPosition(Position position) {
    final location = _locationFromPosition(position);
    if (location == null || !mounted) return;
    setState(() {
      _currentLocation = location;
      _locationState = _LocationState.precise;
      _drivingError = null;
    });
    _updateCalculationsAndMarkers(forceMarkerRefresh: true);
    _followDrivingCamera(location);
    _refreshDrivingRegionIfNeeded(location);
  }

  void _followDrivingCamera(LatLng location) {
    final zoom = _currentZoom < 14 ? 14.0 : _currentZoom;
    _mapController?.animateCamera(
      CameraUpdate.newCameraPosition(
        CameraPosition(target: location, zoom: zoom),
      ),
    );
  }

  void _refreshDrivingRegionIfNeeded(LatLng location) {
    final lastLocation = _lastDrivingFetchLocation;
    final lastFetchAt = _lastDrivingFetchAt;
    final now = DateTime.now();
    if (lastLocation != null && lastFetchAt != null) {
      final movedKm = getDistanceKm(
        lastLocation.latitude,
        lastLocation.longitude,
        location.latitude,
        location.longitude,
      );
      final movedMeters = (movedKm ?? 0) * 1000;
      final tooSoon = now.difference(lastFetchAt) < _drivingFetchInterval;
      if (movedMeters < _drivingFetchMoveMeters || tooSoon) return;
    }

    _lastDrivingFetchLocation = location;
    _lastDrivingFetchAt = now;
    unawaited(_fetchStationsForRegion(
      location,
      maxDistMeters: _drivingFetchRadiusMeters,
      maxResults: 300,
    ));
  }

  void _stopDrivingMode() {
    _drivingPositionSubscription?.cancel();
    _drivingPositionSubscription = null;
    if (!mounted) return;
    setState(() {
      _drivingModeEnabled = false;
      _isStartingDrivingMode = false;
      _drivingError = null;
      _lastDrivingFetchLocation = null;
      _lastDrivingFetchAt = null;
    });
  }

  Future<void> _openDirectionsToStation(Station station) async {
    unawaited(AnalyticsService.logDirectionsRequested(
      stationId: station.id,
      brand: station.brand,
    ));
    final latitude = station.latitude;
    final longitude = station.longitude;
    if (latitude == null || longitude == null) return;

    final uri = Uri.parse('google.navigation:q=$latitude,$longitude&mode=d');
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
        return;
      }
      final webUri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&destination=$latitude,$longitude',
      );
      await launchUrl(webUri, mode: LaunchMode.externalApplication);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Yol tarifi açılamadı.')),
      );
    }
  }

  void _scheduleMarkerRefresh({
    bool force = false,
    Duration delay = Duration.zero,
  }) {
    if (!mounted) return;
    final nextBucket = _markerZoomBucket(_currentZoom);
    if (!force && nextBucket == _renderedZoomBucket) return;

    _markerDebouncer?.cancel();
    _markerDebouncer = Timer(delay, () {
      if (!mounted) return;
      unawaited(_buildMarkers());
    });
  }

  Future<void> _buildMarkers() async {
    final buildId = ++_markerBuildSerial;
    final prefs = context.read<UserPreferencesProvider>();
    final selectedFuel = prefs.selectedFuel;
    final smartResult = _smartResult;
    final nearestStationId = _nearestStationId;
    final zoom = _currentZoom;
    final displayStations = _filteredStations(fuelType: selectedFuel);
    final markerFutures = <Future<Marker>>[];

    if (zoom < 11.0 && displayStations.length > 25) {
      final clusters = _clustersForZoom(
        stations: displayStations,
        fuelType: selectedFuel,
        zoom: zoom,
      );
      for (final cluster in clusters) {
        // zoom < 11: tüm cluster'lar (tek istasyonlu dahil) cluster marker olarak göster
        markerFutures.add(_clusterMarkerFor(
          cluster: cluster,
          selectedFuel: selectedFuel,
          zoom: zoom,
        ));
      }
    } else {
      final visibleStations = _stationsForZoom(
        stations: displayStations,
        fuelType: selectedFuel,
        zoom: zoom,
        favoriteStationIds: prefs.favoriteStationIds,
      );
      final useCompactMarkers = zoom < 13;
      for (final station in visibleStations) {
        markerFutures.add(_stationMarkerFor(
          station: station,
          selectedFuel: selectedFuel,
          smartResult: smartResult,
          nearestStationId: nearestStationId,
          compact: useCompactMarkers,
        ));
      }
    }

    final markerList = await Future.wait(markerFutures);
    if (!mounted || buildId != _markerBuildSerial) return;
    _renderedZoomBucket = _markerZoomBucket(zoom);
    _markersNotifier.value = markerList.toSet();
  }

  Future<Marker> _stationMarkerFor({
    required Station station,
    required String selectedFuel,
    required SmartStationResult? smartResult,
    required String? nearestStationId,
    required bool compact,
  }) async {
    final latitude = station.latitude;
    final longitude = station.longitude;
    final priceNum = station.priceValueFor(selectedFuel);
    final trustedPriceNum = station.trustedPriceValueFor(selectedFuel);
    final priceStr = station.priceTextFor(selectedFuel);
    final priceStatus = station.priceStatusFor(selectedFuel);
    final hasPrice = priceNum != null;
    final stationId = station.id.isNotEmpty
        ? station.id

        : '${station.brand}-$latitude-$longitude';
    final isCheapest = trustedPriceNum != null &&
        (_focusMode == MapFocusMode.cheapest ||
            _focusMode == MapFocusMode.smart) &&
        stationId == smartResult?.cheapestStationId;
    final isMostLogical = trustedPriceNum != null &&
        ((_focusMode == MapFocusMode.smart &&
                stationId == smartResult?.mostLogicalStationId) ||
            (_focusMode == MapFocusMode.nearest &&
                stationId == nearestStationId));
    final isSelected = station.id.isNotEmpty && station.id == _visibleStation?.id;
    final icon = await MarkerIconFactory.stationPrice(
      brand: station.brand,
      priceText: formatMarkerPrice(priceStr),
      hasPrice: hasPrice,
      priceStatus: priceStatus,
      isCheapest: isCheapest,
      isMostLogical: isMostLogical,
      compact: compact,
      isSelected: isSelected,
    );

    return Marker(
      markerId: MarkerId(stationId),
      position: LatLng(latitude!, longitude!),
      icon: icon,
      alpha: hasPrice ? 1.0 : 0.5,
      onTap: () {
        _selectStation(station);
      },
    );
  }

  Future<Marker> _clusterMarkerFor({
    required _StationCluster cluster,
    required String selectedFuel,
    required double zoom,
  }) async {
    final icon = await MarkerIconFactory.cluster(
      count: cluster.stations.length,
    );

    return Marker(
      markerId: MarkerId('cluster:${cluster.id}'),
      position: cluster.center,
      icon: icon,
      onTap: () {
        _mapController?.animateCamera(
          CameraUpdate.newCameraPosition(
            CameraPosition(
              target: cluster.center,
              zoom: (zoom + 1.4).clamp(8.5, 15.5).toDouble(),
            ),
          ),
        );
      },
    );
  }

  List<Station> _stationsForZoom({
    required List<Station> stations,
    required String fuelType,
    required double zoom,
    required Set<String> favoriteStationIds,
  }) {
    if (zoom >= 13.2 || stations.length <= 8) {
      return stations;
    }

    // Marka filtresi aktifken ve az istasyon varsa declutter bypass et.
    // Kullanıcı belirli bir markayı seçtiyse o markanın tüm istasyonlarını görmek ister.
    if (_selectedBrands.isNotEmpty && stations.length <= 50) {
      return stations;
    }

    final config = _declutterConfigForZoom(zoom);
    final byCell = <String, _StationCandidate>{};

    for (final station in stations) {
      final latitude = station.latitude;
      final longitude = station.longitude;
      if (latitude == null || longitude == null) continue;

      final latCell = (latitude / config.cellDegrees).floor();
      final lngCell = (longitude / config.cellDegrees).floor();
      final key = '$latCell:$lngCell';
      final price = station.trustedPriceValueFor(fuelType);
      final distanceKm = getDistanceKm(
            _currentLocation.latitude,
            _currentLocation.longitude,
            latitude,
            longitude,
          ) ??
          999;
      var score = _markerPriorityScore(price, distanceKm);
      if (favoriteStationIds.contains(station.id)) {
        score -= 12;
      }
      final candidate = _StationCandidate(station: station, score: score);
      final existing = byCell[key];
      if (existing == null || candidate.score < existing.score) {
        byCell[key] = candidate;
      }
    }

    final candidates = byCell.values.toList()
      ..sort((a, b) => a.score.compareTo(b.score));
    return candidates
        .take(config.maxMarkers)
        .map((candidate) => candidate.station)
        .toList();
  }

  List<_StationCluster> _clustersForZoom({
    required List<Station> stations,
    required String fuelType,
    required double zoom,
  }) {
    final config = _declutterConfigForZoom(zoom);
    final byCell = <String, List<Station>>{};

    for (final station in stations) {
      final latitude = station.latitude;
      final longitude = station.longitude;
      if (latitude == null || longitude == null) continue;

      final latCell = (latitude / config.cellDegrees).floor();
      final lngCell = (longitude / config.cellDegrees).floor();
      byCell.putIfAbsent('$latCell:$lngCell', () => []).add(station);
    }

    final clusters = byCell.entries
        .map((entry) => _StationCluster.fromStations(entry.key, entry.value))
        .toList()
      ..sort((a, b) => _clusterPriorityScore(a, fuelType)
          .compareTo(_clusterPriorityScore(b, fuelType)));

    return clusters.take(config.maxMarkers).toList(growable: false);
  }

  _DeclutterConfig _declutterConfigForZoom(double zoom) {
    if (zoom < 7.8) {
      return const _DeclutterConfig(cellDegrees: 0.55, maxMarkers: 8);
    }
    if (zoom < 8.5) {
      return const _DeclutterConfig(cellDegrees: 0.38, maxMarkers: 12);
    }
    if (zoom < 9.5) {
      return const _DeclutterConfig(cellDegrees: 0.24, maxMarkers: 20);
    }
    if (zoom < 10.5) {
      return const _DeclutterConfig(cellDegrees: 0.14, maxMarkers: 35);
    }
    if (zoom < 11.5) {
      return const _DeclutterConfig(cellDegrees: 0.075, maxMarkers: 65);
    }
    return const _DeclutterConfig(cellDegrees: 0.04, maxMarkers: 110);
  }

  int _markerZoomBucket(double zoom) {
    if (zoom >= 13.2) return 7;
    if (zoom >= 12.2) return 6;
    if (zoom >= 11.5) return 5;
    if (zoom >= 10.5) return 4;
    if (zoom >= 9.5) return 3;
    if (zoom >= 8.5) return 2;
    if (zoom >= 7.8) return 1;
    return 0;
  }

  int _maxResultsForZoom(double zoom) {
    if (zoom < 8.5) return 120;
    if (zoom < 10.5) return 180;
    if (zoom < 12.2) return 240;
    if (zoom < 13.5) return 260;
    return 180;
  }

  bool _shouldFetchRegion(LatLng center, double radiusMeters) {
    final previousCenter = _lastFetchCenter;
    final previousRadius = _lastFetchRadiusMeters;
    if (previousCenter == null || previousRadius == null) return true;

    final movedKm = getDistanceKm(
      previousCenter.latitude,
      previousCenter.longitude,
      center.latitude,
      center.longitude,
    );
    if (movedKm == null) return true;

    final movedMeters = movedKm * 1000;
    final radiusBase = previousRadius <= 1 ? 1.0 : previousRadius;
    final radiusDelta = (radiusMeters - previousRadius).abs() / radiusBase;
    return movedMeters > radiusMeters * 0.35 || radiusDelta > 0.35;
  }

  double _markerPriorityScore(double? price, double distanceKm) {
    if (_focusMode == MapFocusMode.nearest) return distanceKm;
    if (price == null) return 10000 + distanceKm;
    if (_focusMode == MapFocusMode.cheapest) return price;
    return price + (distanceKm * 0.03);
  }

  double _clusterPriorityScore(_StationCluster cluster, String fuelType) {
    final minPrice = cluster.minPriceFor(fuelType);
    final distanceKm = getDistanceKm(
          _currentLocation.latitude,
          _currentLocation.longitude,
          cluster.center.latitude,
          cluster.center.longitude,
        ) ??
        999;
    return _markerPriorityScore(minPrice, distanceKm) -
        (cluster.stations.length * 0.01);
  }

  @override
  void dispose() {
    _authSubscription?.cancel();
    _fetchDebouncer?.cancel();
    _markerDebouncer?.cancel();
    _drivingPositionSubscription?.cancel();
    _mapController?.dispose();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Re-calculate when preferences change
    if (!_isLoading) {
      _updateCalculationsAndMarkers(forceMarkerRefresh: true);
    }
  }

  Widget _buildFuelChipBar(UserPreferencesProvider prefs) {
    const fuels = [
      ('Benzin', 'Kursunsuz 95'),
      ('Motorin', 'Motorin'),
      ('LPG', 'LPG'),
      ('Şarj', 'Elektrik'),
    ];
    final isDark = _currentIsDark;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: fuels.map((fuel) {
          final (label, fuelKey) = fuel;
          final isSelected = prefs.selectedFuel == fuelKey;
          return Expanded(
            child: GestureDetector(
              onTap: () {
                prefs.setSelectedFuel(fuelKey);
                unawaited(AnalyticsService.logFuelTypeChanged(fuelKey));
                setState(() => _visibleStation = null);
                _updateCalculationsAndMarkers(forceMarkerRefresh: true);
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                margin: const EdgeInsets.symmetric(horizontal: 4),
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: isSelected
                      ? FulColors.primary
                      : (isDark
                          ? FulColors.darkSurface.withOpacity(0.95)
                          : Colors.white.withOpacity(0.95)),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isSelected
                        ? FulColors.primary
                        : (isDark
                            ? FulColors.darkBorder
                            : FulColors.lightBorder),
                    width: 1.2,
                  ),
                  boxShadow: isSelected
                      ? [
                          BoxShadow(
                            color: FulColors.primary.withOpacity(0.4),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          )
                        ]
                      : [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.04),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          )
                        ],
                ),
                child: Center(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 12,
                      fontWeight:
                          isSelected ? FontWeight.w800 : FontWeight.w600,
                      color: isSelected
                          ? Colors.white
                          : (isDark ? FulColors.darkText : FulColors.lightText),
                      letterSpacing: -0.3,
                    ),
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildBrandFilterBar() {
    final isDark = _currentIsDark;

    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: brandOptions.length + 1,
        separatorBuilder: (_, __) => const SizedBox(width: 7),
        itemBuilder: (context, index) {
          if (index == 0) {
            return _BrandFilterChip(
              label: 'Tümü',
              isSelected: _selectedBrands.isEmpty,
              isDark: isDark,
              onTap: _clearBrandFilters,
            );
          }
          final brand = brandOptions[index - 1];
          return _BrandFilterChip(
            label: brand.displayLabel,
            isSelected: _selectedBrands.contains(brand.key),
            isDark: isDark,
            onTap: () => _toggleBrandFilter(brand.key),
          );
        },
      ),
    );
  }

  Widget _buildFabButton({
    IconData? icon,
    bool loading = false,
    required VoidCallback onTap,
    bool active = false,
    Color activeColor = FulColors.primary,
  }) {
    final isDark = _currentIsDark;
    final bg =
        active ? activeColor : (isDark ? FulColors.darkSurface : Colors.white);
    final iconColor = active
        ? Colors.white
        : (isDark ? FulColors.darkText : FulColors.lightText);

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 46,
        height: 46,
        decoration: BoxDecoration(
          color: bg,
          shape: BoxShape.circle,
          border: Border.all(
            color: active
                ? activeColor
                : (isDark ? FulColors.darkBorder : const Color(0xFFE2E8F0)),
            width: 1.4,
          ),
          boxShadow: [
            BoxShadow(
              color: active
                  ? activeColor.withOpacity(0.4)
                  : Colors.black.withOpacity(0.15),
              offset: const Offset(0, 4),
              blurRadius: 12,
            ),
          ],
        ),
        child: Center(
          child: loading
              ? SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.5,
                    color: active ? Colors.white : FulColors.primary,
                  ),
                )
              : Icon(icon, color: iconColor, size: 22),
        ),
      ),
    );
  }

  String? get _statusMessage {
    if (_stationLoadError != null) return _stationLoadError;
    if (_drivingError != null) return _drivingError;
    switch (_locationState) {
      case _LocationState.serviceOff:
        return 'Konum servisi kapalı — haritayı kaydırarak istasyon ara.';
      case _LocationState.denied:
        return 'Konum izni verilmedi — haritayı kaydırarak istasyon ara.';
      case _LocationState.fallback:
        return null;
      case _LocationState.checking:
      case _LocationState.precise:
        return null;
    }
  }

  Widget _buildStatusBanner() {
    final message = _statusMessage;
    if (message == null) return const SizedBox.shrink();
    final isError = _stationLoadError != null || _drivingError != null;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 22),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.94),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isError ? const Color(0xFFFECACA) : const Color(0xFFE5E7EB),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.10),
            offset: const Offset(0, 4),
            blurRadius: 12,
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isError ? Icons.cloud_off_rounded : Icons.location_off_rounded,
            size: 16,
            color: isError ? const Color(0xFFDC2626) : const Color(0xFF6B7280),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              message,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Color(0xFF374151),
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          if (isError) ...[
            const SizedBox(width: 10),
            GestureDetector(
              onTap: _drivingError != null
                  ? _startDrivingMode
                  : _retryStationFetch,
              child: const Text(
                'Tekrar dene',
                style: TextStyle(
                  color: Color(0xFFFF5A5F),
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDrivingBanner(UserPreferencesProvider prefs) {
    if (!_drivingModeEnabled) return const SizedBox.shrink();
    final station = _drivingTargetStation(prefs.selectedFuel);
    final distance = _distanceToStation(station);
    final priceText = station?.priceTextFor(prefs.selectedFuel);
    final stationLine = station == null
        ? (_isFetchingStations
            ? 'Yakındaki istasyonlar güncelleniyor'
            : 'Seçili yakıt için yakın istasyon aranıyor')
        : '${station.brand} • ${distance?.toStringAsFixed(1) ?? '-'} km • ${priceText ?? '-'} TL';

    return GestureDetector(
      onTap:
          station == null ? null : () => _selectStation(station, animate: true),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 18),
        padding: const EdgeInsets.fromLTRB(14, 11, 10, 11),
        decoration: BoxDecoration(
          color: const Color(0xFF111827).withOpacity(0.96),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: const Color(0xFF10B981), width: 1.2),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.20),
              offset: const Offset(0, 8),
              blurRadius: 18,
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: const BoxDecoration(
                color: Color(0xFF10B981),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.navigation_rounded,
                color: Colors.white,
                size: 19,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Sürüş takibi açık',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    stationLine,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFFD1FAE5),
                      fontWeight: FontWeight.w800,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            if (station != null) ...[
              const SizedBox(width: 8),
              GestureDetector(
                onTap: () => _openDirectionsToStation(station),
                child: Container(
                  height: 34,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: const Text(
                    'Git',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 12,
                    ),
                  ),
                ),
              ),
            ],
            const SizedBox(width: 6),
            GestureDetector(
              onTap: _stopDrivingMode,
              child: const SizedBox(
                width: 30,
                height: 34,
                child: Icon(
                  Icons.close_rounded,
                  color: Color(0xFFD1D5DB),
                  size: 20,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _retryStationFetch() {
    _fetchStationsForRegion(
      _lastFetchCenter ?? _currentLocation,
      maxDistMeters: _lastFetchRadiusMeters ?? 20000,
      maxResults: _maxResultsForZoom(_currentZoom),
      brandKeys: _selectedBrands,
    );
  }

  void _clearBrandFilters() {
    if (_selectedBrands.isEmpty) return;
    final center = _lastFetchCenter ?? _currentLocation;
    final radius = _lastFetchRadiusMeters ?? 20000;
    setState(() {
      _selectedBrands = {};
      _visibleStation = null;
    });
    unawaited(AnalyticsService.logBrandFilterChanged(const []));
    unawaited(_fetchStationsForRegion(
      center,
      maxDistMeters: radius,
      maxResults: _maxResultsForZoom(_currentZoom),
      brandKeys: const {},
    ));
  }

  void _toggleBrandFilter(String brandKey) {
    final next = {..._selectedBrands};
    if (next.contains(brandKey)) {
      next.remove(brandKey);
    } else {
      next.add(brandKey);
    }
    final center = _lastFetchCenter ?? _currentLocation;
    final radius = _lastFetchRadiusMeters ?? 20000;
    setState(() {
      _selectedBrands = next;
      _visibleStation = null;
    });
    unawaited(AnalyticsService.logBrandFilterChanged(
      brandLabelsForKeys(next),
    ));
    unawaited(_fetchStationsForRegion(
      center,
      maxDistMeters: radius,
      maxResults: _maxResultsForZoom(_currentZoom),
      brandKeys: next,
    ));
  }

  void _openGarage() {
    unawaited(AnalyticsService.logGarageOpened());
    GarageBottomSheet.show(context, isDark: _currentIsDark);
  }

  void _openSettings() {
    setState(() => _menuOpen = false);
    SettingsSheet.show(
      context,
      isDark: _currentIsDark,
      appVersion: '1.0.2',
      currentUser: _currentUser,
      stations: _stations,
      onSignIn: _onSignInTapped,
      onSignOut: () async => AuthService.signOut(),
    );
  }

  void _showStationSearch() {
    final prefs = context.read<UserPreferencesProvider>();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _StationSearchSheet(
        stationsFuture: SupabaseService.fetchAllActiveStationsSafe(),
        location: _currentLocation,
        selectedFuel: prefs.selectedFuel,
        selectedBrands: _selectedBrands,
        favoriteStationIds: prefs.favoriteStationIds,
        recentStationIds: prefs.recentStationIds,
        isDark: _currentIsDark,
        onSearchSubmitted: (query) =>
            unawaited(AnalyticsService.logSearchPerformed(query)),
        onStationSelected: (station) {
          _selectStation(station, animate: true);
        },
      ),
    );
  }

  void _selectStation(Station station, {bool animate = false}) {
    final prefs = context.read<UserPreferencesProvider>();
    if (station.id.isNotEmpty) {
      unawaited(prefs.rememberStation(station.id));
    }
    unawaited(AnalyticsService.logStationTapped(
      stationId: station.id,
      brand: station.brand,
      selectedFuel: prefs.selectedFuel,
      price: station.priceValueFor(prefs.selectedFuel),
    ));
    setState(() {
      _visibleStation = station;
      _menuOpen = false;
    });
    unawaited(_buildMarkers()); // Refresh selected marker state
    if (!animate) return;

    final latitude = station.latitude;
    final longitude = station.longitude;
    if (latitude == null || longitude == null) return;
    // Shift camera slightly south so the pin appears above the bottom sheet peek
    _mapController?.animateCamera(
      CameraUpdate.newCameraPosition(
        CameraPosition(
          target: LatLng(latitude - 0.004, longitude),
          zoom: 14.2,
        ),
      ),
    );
  }

  Widget _buildEmptyState(UserPreferencesProvider prefs) {
    final hasBrandFilter = _selectedBrands.isNotEmpty;
    final hasError = _stationLoadError != null;
    final selectedBrandText = brandFilterSummary(_selectedBrands);
    final fuelText =
        prefs.selectedFuel == 'Kursunsuz 95' ? 'Benzin' : prefs.selectedFuel;
    final title = hasError
        ? 'Veri alınamadı'
        : hasBrandFilter
            ? 'Bu bölgede $selectedBrandText yok'
            : 'Bu bölgede fiyat bulunamadı';
    final description = hasError
        ? 'Bağlantıyı kontrol edip tekrar deneyebilirsin.'
        : hasBrandFilter
            ? '$selectedBrandText için $fuelText fiyatı bu harita alanında görünmüyor. Haritayı kaydırarak farklı bölgede ara veya filtreyi temizle.'
            : '$fuelText için doğrulanmış fiyat verisi görünmüyor.';
    final actionLabel = hasError
        ? 'Tekrar dene'
        : hasBrandFilter
            ? 'Filtreyi temizle'
            : null;

    return Positioned(
      top: MediaQuery.of(context).size.height * 0.34,
      left: 26,
      right: 26,
      child: Center(
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.95),
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: const Color(0xFFE5E7EB)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.14),
                offset: const Offset(0, 8),
                blurRadius: 18,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                hasError
                    ? Icons.cloud_off_rounded
                    : Icons.local_gas_station_outlined,
                color: hasError
                    ? const Color(0xFFDC2626)
                    : const Color(0xFF6B7280),
                size: 28,
              ),
              const SizedBox(height: 8),
              Text(
                title,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Color(0xFF111827),
                  fontWeight: FontWeight.w900,
                  fontSize: 15,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Color(0xFF6B7280),
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                  height: 1.35,
                ),
              ),
              if (actionLabel != null) ...[
                const SizedBox(height: 12),
                GestureDetector(
                  onTap: hasError ? _retryStationFetch : _clearBrandFilters,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFF5A5F),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      actionLabel,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final prefs = context.watch<UserPreferencesProvider>();

    return Scaffold(
      body: Stack(
        children: [
          // ValueListenableBuilder ile sarmalayarak sadece marker değiştiğinde
          // haritayı render etmesini, bütün arayüzü tekrar çizmemesini sağlıyoruz
          ValueListenableBuilder<Set<Marker>>(
            valueListenable: _markersNotifier,
            builder: (context, markers, child) {
              return GoogleMap(
                key: const ValueKey('main_google_map'),
                mapType: MapType.normal,
                initialCameraPosition:
                    CameraPosition(target: _currentLocation, zoom: 12),
                myLocationEnabled: _locationState == _LocationState.precise ||
                    _locationState == _LocationState.fallback,
                myLocationButtonEnabled: false,
                zoomControlsEnabled: false,
                compassEnabled: false,
                mapToolbarEnabled: false,
                buildingsEnabled: false,
                trafficEnabled: false,
                markers: markers,
                onMapCreated: (controller) {
                  _mapController = controller;
                  // Başlangıç harita stilini uygula
                  final style = _currentIsDark
                      ? FulTheme.darkMapStyle
                      : FulTheme.lightMapStyle;
                  controller.setMapStyle(style);
                },
                onCameraMove: (position) {
                  final previousBucket = _markerZoomBucket(_currentZoom);
                  _currentZoom = position.zoom;
                  if (_markerZoomBucket(position.zoom) != previousBucket) {
                    _scheduleMarkerRefresh(
                      force: true,
                      delay: const Duration(milliseconds: 80),
                    );
                  }
                },
                onTap: (_) {
                  if (_visibleStation == null) return;
                  setState(() => _visibleStation = null);
                  unawaited(_buildMarkers());
                },
                onCameraIdle: () async {
                  if (_mapController == null) return;
                  _scheduleMarkerRefresh(force: true);

                  final bounds = await _mapController!.getVisibleRegion();
                  final center = LatLng(
                      (bounds.northeast.latitude + bounds.southwest.latitude) /
                          2,
                      (bounds.northeast.longitude +
                              bounds.southwest.longitude) /
                          2);
                  final radiusKm = getDistanceKm(
                        center.latitude,
                        center.longitude,
                        bounds.northeast.latitude,
                        bounds.northeast.longitude,
                      ) ??
                      20;
                  final maxDistMeters =
                      (radiusKm * 1400).clamp(3000, 100000).toDouble();
                  final maxResults = _maxResultsForZoom(_currentZoom);
                  if (!_shouldFetchRegion(center, maxDistMeters)) return;

                  _fetchDebouncer?.cancel();
                  _fetchDebouncer =
                      Timer(const Duration(milliseconds: 450), () {
                    _fetchStationsForRegion(
                      center,
                      maxDistMeters: maxDistMeters,
                      maxResults: maxResults,
                      brandKeys: _selectedBrands,
                    );
                  });
                },
              );
            },
          ),

          Positioned(
            top: MediaQuery.of(context).padding.top + 10,
            left: 0,
            right: 0,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TopSearchBar(
                  onMenuTap: () => setState(() {
                    HapticFeedback.lightImpact();
                    _visibleStation = null; // Close bottom sheet if open
                    _menuOpen = true;
                  }),
                  onSearchTap: _showStationSearch,
                  onGarageTap: _openGarage,
                  selectedFuel: prefs.selectedFuel,
                  focusMode: _focusMode,
                  isDark: _currentIsDark,
                ),
                const SizedBox(height: 8),
                // Yakıt tipi chip bar — Trugo tarzı
                _buildFuelChipBar(prefs),
                const SizedBox(height: 8),
                _buildBrandFilterBar(),
                if (_statusMessage != null) ...[
                  const SizedBox(height: 8),
                  _buildStatusBanner(),
                ],
                if (_drivingModeEnabled) ...[
                  const SizedBox(height: 8),
                  _buildDrivingBanner(prefs),
                ],
                if (_isFetchingStations) ...[
                  const SizedBox(height: 6),
                  Center(
                    child: Container(
                      width: 120,
                      height: 3,
                      clipBehavior: Clip.hardEdge,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: const LinearProgressIndicator(
                        backgroundColor: Colors.transparent,
                        color: FulColors.primary,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),

          // Sağ FAB Yığını — her zaman aynı konumda
          Positioned(
            right: 14,
            bottom: 110,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Dark mode toggle
                _buildFabButton(
                  icon: _currentIsDark
                      ? Icons.light_mode_rounded
                      : Icons.dark_mode_rounded,
                  onTap: () {
                    setState(() {
                      _isDarkModeOverride = !_currentIsDark;
                    });
                    final style = _currentIsDark
                        ? FulTheme.darkMapStyle
                        : FulTheme.lightMapStyle;
                    _mapController?.setMapStyle(style);
                  },
                  active: _currentIsDark,
                ),
                const SizedBox(height: 10),
                // Konumuma git
                _buildFabButton(
                  icon: Icons.my_location_rounded,
                  onTap: () {
                    if (_mapController != null) {
                      _mapController!.animateCamera(
                        CameraUpdate.newCameraPosition(
                          CameraPosition(target: _currentLocation, zoom: 14),
                        ),
                      );
                    }
                  },
                  active: false,
                ),
                const SizedBox(height: 10),
                // Sürüş takibi
                _buildFabButton(
                  icon:
                      _isStartingDrivingMode ? null : Icons.navigation_rounded,
                  loading: _isStartingDrivingMode,
                  onTap: _toggleDrivingMode,
                  active: _drivingModeEnabled,
                  activeColor: FulColors.logical,
                ),
              ],
            ),
          ),

          if (_filteredStations(fuelType: prefs.selectedFuel).isEmpty &&
              !_isLoading)
            _buildEmptyState(prefs),

          if (_isLoading)
            const Positioned(
              top: 150,
              left: 0,
              right: 0,
              child: Center(
                child: CircularProgressIndicator(color: Color(0xFFFF5A5F)),
              ),
            ),

          // Sol Yan Menü — Trugo tarzı
          // Side menu her zaman render edilir, açık/kapalı state'ini kendi yönetip kayarak çıkar
          Positioned(
            left: 12,
            bottom: _visibleStation != null ? 290 : 100,
            child: _buildMarkerLegend(),
          ),

          Consumer<UserPreferencesProvider>(
            builder: (_, prefs, __) => FulSideMenu(
              isOpen: _menuOpen,
              isDark: _currentIsDark,
              onClose: () => setState(() => _menuOpen = false),
              focusMode: _focusMode,
              onFocusModeChanged: (mode) {
                setState(() {
                  _focusMode = mode;
                  _menuOpen = false;
                });
                unawaited(AnalyticsService.logFocusModeChanged(mode.name));
                _updateCalculationsAndMarkers(forceMarkerRefresh: true);
              },
              news: _news,
              stationCount: _stations.length,
              appVersion: '1.0.2',
              allStations: _stations,
              favoriteStationIds: prefs.favoriteStationIds,
              selectedFuel: prefs.selectedFuel,
              onStationSelected: (station) =>
                  _selectStation(station, animate: true),
              currentUser: _currentUser,
              onSignIn: _onSignInTapped,
              onSignOut: () async {
                await AuthService.signOut();
              },
              onSettingsTap: _openSettings,
            ),
          ),

          // Alt Panel (Bottom Sheet) — İstasyon Detayları
          if (_visibleStation != null)
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: StationBottomSheet(
                visibleStation: _visibleStation,
                location: _currentLocation,
                selectedFuel: prefs.selectedFuel,
                isFavorite: prefs.isFavoriteStation(_visibleStation!.id),
                onFavoriteToggle: () {
                  final st = _visibleStation;
                  if (st == null) return;
                  final willFavorite = !prefs.isFavoriteStation(st.id);
                  prefs.toggleFavoriteStation(st.id);
                  unawaited(AnalyticsService.logFavoriteToggled(
                    stationId: st.id,
                    isFavorited: willFavorite,
                  ));
                },
                hasVehicle: prefs.hasVehicle,
                onGaragePromptTap: _openGarage,
                onGaragePromptClose: () {
                  setState(() => _visibleStation = null);
                  unawaited(_buildMarkers());
                },
                onDirectionsRequested: (station) =>
                    AnalyticsService.logDirectionsRequested(
                  stationId: station.id,
                  brand: station.brand,
                ),
                closeSheet: () {
                  setState(() => _visibleStation = null);
                  unawaited(_buildMarkers());
                },
                smartScore: _smartResult != null
                    ? SmartStationService.calculateSmartScore(
                        station: _visibleStation!,
                        location: _currentLocation,
                        selectedFuel: prefs.selectedFuel,
                        tankCapacity: prefs.tankCapacity,
                        fuelConsumption: prefs.fuelConsumption,
                        bestResult: _smartResult!,
                      )
                    : null,
                tankCapacity: prefs.tankCapacity,
                fuelConsumption: prefs.fuelConsumption,
                onPriceAlertTap: () {
                  final st = _visibleStation;
                  if (st == null) return;
                  PriceAlertDialog.show(
                    context,
                    station: st,
                    fuelType: prefs.selectedFuel,
                    currentPrice: st.priceValueFor(prefs.selectedFuel),
                    currentUserId: _currentUser?.uid,
                    onSignIn: _onSignInTapped,
                    isDark: _currentIsDark,
                  );
                },
                onPurchaseConfirmed: () {
                  final st = _visibleStation;
                  if (st == null || _smartResult == null) return;
                  final score = SmartStationService.calculateSmartScore(
                    station: st,
                    location: _currentLocation,
                    selectedFuel: prefs.selectedFuel,
                    tankCapacity: prefs.tankCapacity,
                    fuelConsumption: prefs.fuelConsumption,
                    bestResult: _smartResult!,
                  );
                  if (score == null) return;
                  unawaited(SavingsService.recordPurchase(score.savingsTL));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text(
                          'Kaydedildi — tahmini tasarrufun güncellendi'),
                    ),
                  );
                },
              )
                  .animate()
                  .slideY(
                      begin: 1.0,
                      end: 0.0,
                      duration: 300.ms,
                      curve: Curves.easeOutCubic)
                  .fadeIn(duration: 200.ms),
            ),
        ],
      ),
    );
  }

  Widget _buildMarkerLegend() {
    final isDark = _currentIsDark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: isDark
            ? FulColors.darkSurface.withOpacity(0.92)
            : Colors.white.withOpacity(0.92),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDark ? FulColors.darkBorder : FulColors.lightBorder,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.12),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: const Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _LegendItem(color: FulColors.logical, label: 'En mantıklı'),
          SizedBox(height: 4),
          _LegendItem(color: FulColors.cheapest, label: 'En ucuz'),
          SizedBox(height: 4),
          _LegendItem(color: FulColors.primary, label: 'Diğer'),
        ],
      ),
    );
  }
}

class _BrandFilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final bool isDark;
  final VoidCallback onTap;

  const _BrandFilterChip({
    required this.label,
    required this.isSelected,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final textColor = isSelected
        ? Colors.white
        : (isDark ? FulColors.darkText : FulColors.lightText);
    final border = isSelected
        ? FulColors.primary
        : (isDark ? FulColors.darkBorder : FulColors.lightBorder);

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 12),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: isSelected
              ? FulColors.primary
              : (isDark
                  ? FulColors.darkSurface.withOpacity(0.94)
                  : Colors.white.withOpacity(0.94)),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: border, width: 1.1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 5,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: 'Outfit',
            fontSize: 12,
            fontWeight: FontWeight.w800,
            color: textColor,
          ),
        ),
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendItem({
    required this.color,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: TextStyle(
            fontFamily: 'Outfit',
            fontSize: 10,
            fontWeight: FontWeight.w800,
            color: color,
          ),
        ),
      ],
    );
  }
}

class _SearchBadge extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final Color backgroundColor;

  const _SearchBadge({
    required this.label,
    required this.icon,
    required this.color,
    required this.backgroundColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _SearchModeChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool selected;
  final bool isDark;
  final VoidCallback onTap;

  const _SearchModeChip({
    required this.label,
    required this.icon,
    required this.selected,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final unselectedBg = isDark ? FulColors.darkCard : Colors.white;
    const selectedFg = Colors.white;
    final unselectedFg = isDark ? FulColors.darkText : FulColors.lightText;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: selected ? FulColors.primary : unselectedBg,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected
                ? Colors.transparent
                : (isDark ? FulColors.darkBorder : const Color(0xFFE5E7EB)),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 16, color: selected ? selectedFg : unselectedFg),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontFamily: 'Outfit',
                fontWeight: FontWeight.w700,
                fontSize: 13,
                color: selected ? selectedFg : unselectedFg,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DeclutterConfig {
  final double cellDegrees;
  final int maxMarkers;

  const _DeclutterConfig({
    required this.cellDegrees,
    required this.maxMarkers,
  });
}

class _StationCandidate {
  final Station station;
  final double score;

  const _StationCandidate({
    required this.station,
    required this.score,
  });
}

class _StationCluster {
  final String id;
  final LatLng center;
  final List<Station> stations;

  const _StationCluster({
    required this.id,
    required this.center,
    required this.stations,
  });

  factory _StationCluster.fromStations(String id, List<Station> stations) {
    var latTotal = 0.0;
    var lngTotal = 0.0;
    var count = 0;
    for (final station in stations) {
      final latitude = station.latitude;
      final longitude = station.longitude;
      if (latitude == null || longitude == null) continue;
      latTotal += latitude;
      lngTotal += longitude;
      count += 1;
    }

    return _StationCluster(
      id: id,
      center: LatLng(latTotal / count, lngTotal / count),
      stations: stations,
    );
  }

  double? minPriceFor(String fuelType) {
    double? best;
    for (final station in stations) {
      final price = station.trustedPriceValueFor(fuelType);
      if (price == null) continue;
      if (best == null || price < best) best = price;
    }
    return best;
  }
}

class _StationSearchSheet extends StatefulWidget {
  final Future<List<Station>> stationsFuture;
  final LatLng location;
  final String selectedFuel;
  final Set<String> selectedBrands;
  final Set<String> favoriteStationIds;
  final List<String> recentStationIds;
  final bool isDark;
  final ValueChanged<String> onSearchSubmitted;
  final ValueChanged<Station> onStationSelected;

  const _StationSearchSheet({
    required this.stationsFuture,
    required this.location,
    required this.selectedFuel,
    required this.selectedBrands,
    required this.favoriteStationIds,
    required this.recentStationIds,
    this.isDark = false,
    required this.onSearchSubmitted,
    required this.onStationSelected,
  });

  @override
  State<_StationSearchSheet> createState() => _StationSearchSheetState();
}

enum _SearchSheetMode { search, byPrice }

class _StationSearchSheetState extends State<_StationSearchSheet> {
  final TextEditingController _controller = TextEditingController();
  String _query = '';
  Timer? _debounce;
  _SearchSheetMode _mode = _SearchSheetMode.search;

  @override
  void dispose() {
    _controller.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearch(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), () {
      if (mounted) setState(() => _query = value);
      final query = value.trim();
      if (query.length >= 2) widget.onSearchSubmitted(query);
    });
  }

  @override
  Widget build(BuildContext context) {
    // isDark parametreden geliyor — MaterialApp teması değişmediği için
    // Theme.of(context).brightness her zaman light döner
    final isDark = widget.isDark;
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: Container(
        height: (MediaQuery.of(context).size.height * 0.88) - bottomInset,
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 18),
        decoration: BoxDecoration(
          color: isDark ? FulColors.darkSurface : const Color(0xFFF9FAFB),
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(26),
            topRight: Radius.circular(26),
          ),
        ),
        child: Column(
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 44,
                height: 5,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color:
                      isDark ? FulColors.darkBorder : const Color(0xFFD1D5DB),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            Row(
              children: [
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: isDark ? FulColors.darkCard : Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: isDark
                            ? FulColors.darkBorder
                            : const Color(0xFFE5E7EB),
                      ),
                    ),
                    child: TextField(
                      controller: _controller,
                      autofocus: true,
                      textInputAction: TextInputAction.search,
                      onChanged: _onSearch,
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        color:
                            isDark ? FulColors.darkText : FulColors.lightText,
                        fontWeight: FontWeight.w600,
                      ),
                      decoration: InputDecoration(
                        hintText: 'İstasyon, marka, il veya ilçe ara...',
                        hintStyle: TextStyle(
                          fontFamily: 'Outfit',
                          color: isDark
                              ? FulColors.darkTextMuted
                              : FulColors.lightTextMuted,
                          fontWeight: FontWeight.w500,
                        ),
                        prefixIcon: Icon(
                          Icons.search_rounded,
                          color: isDark
                              ? FulColors.darkTextMuted
                              : FulColors.lightTextMuted,
                        ),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 14),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                GestureDetector(
                  onTap: () => Navigator.pop(context),
                  child: Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: isDark ? FulColors.darkCard : Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: isDark
                            ? FulColors.darkBorder
                            : const Color(0xFFE5E7EB),
                      ),
                    ),
                    child: Icon(
                      Icons.close_rounded,
                      color: isDark ? FulColors.darkText : FulColors.lightText,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _SearchModeChip(
                    label: 'Ara',
                    icon: Icons.search_rounded,
                    selected: _mode == _SearchSheetMode.search,
                    isDark: isDark,
                    onTap: () => setState(() => _mode = _SearchSheetMode.search),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SearchModeChip(
                    label: 'Fiyata Göre',
                    icon: Icons.sort_rounded,
                    selected: _mode == _SearchSheetMode.byPrice,
                    isDark: isDark,
                    onTap: () =>
                        setState(() => _mode = _SearchSheetMode.byPrice),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Expanded(
              child: FutureBuilder<List<Station>>(
                future: widget.stationsFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done) {
                    return const Center(
                      child:
                          CircularProgressIndicator(color: FulColors.primary),
                    );
                  }
                  final stations = snapshot.data ?? const <Station>[];
                  // Kullanıcı henüz bir şey yazmadıysa prompt göster (flicker engeli)
                  if (_mode == _SearchSheetMode.search && _query.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.search_rounded,
                              size: 48,
                              color: isDark
                                  ? FulColors.darkTextMuted
                                  : const Color(0xFFD1D5DB)),
                          const SizedBox(height: 12),
                          Text(
                            'Arama yapın',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontWeight: FontWeight.w800,
                              fontSize: 17,
                              color: isDark
                                  ? FulColors.darkText
                                  : FulColors.lightText,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'İstasyon adı, marka, il veya ilçe girin',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 13,
                              color: isDark
                                  ? FulColors.darkTextMuted
                                  : FulColors.lightTextMuted,
                            ),
                          ),
                        ],
                      ),
                    );
                  }
                  final results = _mode == _SearchSheetMode.byPrice
                      ? _priceSortedResults(stations)
                      : _searchResults(stations);
                  if (results.isEmpty) {
                    final message = _mode == _SearchSheetMode.byPrice
                        ? 'Bu bölgede fiyat bilgisi olan istasyon yok'
                        : '"$_query" için sonuç bulunamadı';
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.search_off_rounded,
                              size: 40,
                              color: isDark
                                  ? FulColors.darkTextMuted
                                  : const Color(0xFFD1D5DB)),
                          const SizedBox(height: 10),
                          Text(
                            message,
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                              color: isDark
                                  ? FulColors.darkTextMuted
                                  : const Color(0xFF6B7280),
                            ),
                          ),
                        ],
                      ),
                    );
                  }
                  return ListView.separated(
                    itemCount: results.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final station = results[index].station;
                      return _SearchResultTile(
                        station: station,
                        selectedFuel: widget.selectedFuel,
                        distanceKm: results[index].distanceKm,
                        isFavorite: results[index].isFavorite,
                        isRecent: results[index].isRecent,
                        onTap: () {
                          Navigator.pop(context);
                          widget.onStationSelected(station);
                        },
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<_SearchResult> _searchResults(List<Station> stations) {
    final query = _normalize(_query);
    var filtered = stations.where((station) {
      if (widget.selectedBrands.isNotEmpty &&
          !widget.selectedBrands.contains(canonicalBrandKey(station.brand))) {
        return false;
      }
      if (!station.isVisibleInApp) {
        return false;
      }
      if (query.isEmpty) return true;
      final haystack = _normalize(
        '${station.brand} ${station.displayName} ${station.city} ${station.district}',
      );
      return haystack.contains(query);
    }).toList();

    if (query.isEmpty) {
      filtered = filtered
          .where((s) =>
              widget.favoriteStationIds.contains(s.id) ||
              widget.recentStationIds.contains(s.id))
          .toList();
    } else if (filtered.length > 50) {
      filtered = filtered.sublist(0, 50);
    }

    final results = filtered.map((station) {
      final distance = getDistanceKm(
        widget.location.latitude,
        widget.location.longitude,
        station.latitude,
        station.longitude,
      );
      return _SearchResult(
        station: station,
        distanceKm: distance,
        isFavorite: widget.favoriteStationIds.contains(station.id),
        recentIndex: widget.recentStationIds.indexOf(station.id),
      );
    }).toList();

    results.sort((a, b) {
      if (query.isNotEmpty) {
        final aStarts = _normalize(a.station.displayName).startsWith(query) ||
            _normalize(a.station.brand).startsWith(query);
        final bStarts = _normalize(b.station.displayName).startsWith(query) ||
            _normalize(b.station.brand).startsWith(query);
        if (aStarts != bStarts) return aStarts ? -1 : 1;
      }
      final pinCompare = _pinRank(a).compareTo(_pinRank(b));
      if (pinCompare != 0) return pinCompare;
      if (query.isEmpty && a.isRecent && b.isRecent) {
        final recentCompare = a.recentIndex.compareTo(b.recentIndex);
        if (recentCompare != 0) return recentCompare;
      }
      return (a.distanceKm ?? double.maxFinite)
          .compareTo(b.distanceKm ?? double.maxFinite);
    });

    return results;
  }

  /// (price_status_rank, fiyat) ile sıralar — bayat/bilinmeyen bir fiyat
  /// doğrulanmış bir fiyattan asla "daha ucuz" görünmez (fresh her zaman
  /// önce), aksi halde ürünün "yanlış fiyat göstermeme" ilkesi ihlal edilir.
  List<_SearchResult> _priceSortedResults(List<Station> stations) {
    final filtered = stations.where((station) {
      if (widget.selectedBrands.isNotEmpty &&
          !widget.selectedBrands.contains(canonicalBrandKey(station.brand))) {
        return false;
      }
      if (!station.isVisibleInApp) return false;
      return station.hasDisplayablePriceFor(widget.selectedFuel);
    }).toList();

    final results = filtered.map((station) {
      final distance = getDistanceKm(
        widget.location.latitude,
        widget.location.longitude,
        station.latitude,
        station.longitude,
      );
      return _SearchResult(
        station: station,
        distanceKm: distance,
        isFavorite: widget.favoriteStationIds.contains(station.id),
        recentIndex: widget.recentStationIds.indexOf(station.id),
      );
    }).toList();

    results.sort((a, b) {
      final rankCompare = priceStatusRank(a.station.priceStatusFor(widget.selectedFuel))
          .compareTo(priceStatusRank(b.station.priceStatusFor(widget.selectedFuel)));
      if (rankCompare != 0) return rankCompare;
      final aPrice = a.station.priceValueFor(widget.selectedFuel) ?? double.maxFinite;
      final bPrice = b.station.priceValueFor(widget.selectedFuel) ?? double.maxFinite;
      return aPrice.compareTo(bPrice);
    });

    return results;
  }

  String _normalize(String value) {
    return value
        .toLowerCase()
        .replaceAll('ı', 'i')
        .replaceAll('ğ', 'g')
        .replaceAll('ü', 'u')
        .replaceAll('ş', 's')
        .replaceAll('ö', 'o')
        .replaceAll('ç', 'c');
  }

  int _pinRank(_SearchResult result) {
    if (result.isFavorite) return 0;
    if (result.isRecent) return 1;
    return 2;
  }
}

class _SearchResult {
  final Station station;
  final double? distanceKm;
  final bool isFavorite;
  final int recentIndex;

  const _SearchResult({
    required this.station,
    required this.distanceKm,
    required this.isFavorite,
    required this.recentIndex,
  });

  bool get isRecent => recentIndex >= 0;
}

class _SearchResultTile extends StatelessWidget {
  final Station station;
  final String selectedFuel;
  final double? distanceKm;
  final bool isFavorite;
  final bool isRecent;
  final VoidCallback onTap;

  const _SearchResultTile({
    required this.station,
    required this.selectedFuel,
    required this.distanceKm,
    required this.isFavorite,
    required this.isRecent,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final price = station.priceTextFor(selectedFuel);
    final priceColor = priceStatusColor(station.priceStatusFor(selectedFuel));
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE5E7EB)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              offset: const Offset(0, 3),
              blurRadius: 8,
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: const Color(0xFF111827),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(
                Icons.local_gas_station_rounded,
                color: Colors.white,
                size: 21,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    station.displayName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF111827),
                      fontWeight: FontWeight.w900,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '${station.brand} • ${station.city} ${station.district}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF6B7280),
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                    ),
                  ),
                  if (isFavorite || isRecent) ...[
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      children: [
                        if (isFavorite)
                          const _SearchBadge(
                            label: 'Favori',
                            icon: Icons.star_rounded,
                            color: Color(0xFFF59E0B),
                            backgroundColor: Color(0xFFFFF7ED),
                          ),
                        if (isRecent)
                          const _SearchBadge(
                            label: 'Son',
                            icon: Icons.history_rounded,
                            color: Color(0xFF2563EB),
                            backgroundColor: Color(0xFFEFF6FF),
                          ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  price == '-' ? 'Yok' : price,
                  style: TextStyle(
                    color: priceColor,
                    fontWeight: FontWeight.w900,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  distanceKm == null
                      ? '-'
                      : '${distanceKm!.toStringAsFixed(1)} km',
                  style: const TextStyle(
                    color: Color(0xFF10B981),
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
