import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/news_item.dart';
import '../models/station.dart';
import '../services/supabase_service.dart';
import '../services/smart_station_service.dart';
import '../providers/user_preferences_provider.dart';
import '../widgets/garage_modal.dart';
import '../widgets/station_bottom_sheet.dart';
import '../utils/price_formatter.dart';
import '../utils/marker_icon_factory.dart';
import '../utils/distance_calculator.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

enum _MapFocusMode { smart, cheapest, nearest }

enum _LocationState { checking, precise, fallback, serviceOff, denied }

class _MapScreenState extends State<MapScreen> {
  static const List<String> _brandOrder = [
    'Shell',
    'Opet',
    'Petrol Ofisi',
    'BP',
    'TotalEnergies',
    'Türkiye Petrolleri',
    'Aytemiz',
  ];
  static const double _drivingFetchRadiusMeters = 30000;
  static const double _drivingFetchMoveMeters = 1200;
  static const Duration _drivingFetchInterval = Duration(seconds: 45);
  static final Uri _privacyPolicyUri = Uri.parse(
    'https://yakupefecaliskann.github.io/Fullet/privacy.html',
  );

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
  Set<Marker> _markers = {};
  double _currentZoom = 12;
  Set<String> _selectedBrands = {};
  _MapFocusMode _focusMode = _MapFocusMode.smart;

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

  @override
  void initState() {
    super.initState();
    _initData();
  }

  Future<void> _initData() async {
    await _getLocation();
    unawaited(_loadNews());
    await _fetchStationsForRegion(_currentLocation);
    if (!mounted) return;
    setState(() => _isLoading = false);
    unawaited(SupabaseService.fetchAllActiveStationsSafe());
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

    try {
      final position = await Geolocator.getCurrentPosition(
              desiredAccuracy: LocationAccuracy.high)
          .timeout(const Duration(seconds: 5));
      final location = _locationFromPosition(position);
      if (!mounted) return;
      setState(() {
        if (location == null) {
          _currentLocation = const LatLng(41.0082, 28.9784);
          _locationState = _LocationState.fallback;
        } else {
          _currentLocation = location;
          _locationState = _LocationState.precise;
        }
      });
      _mapController?.animateCamera(CameraUpdate.newCameraPosition(
        CameraPosition(target: _currentLocation, zoom: 12),
      ));
    } catch (e) {
      _setDefaultLocation(_LocationState.fallback);
    }
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
    if (position.latitude < 35 ||
        position.latitude > 43 ||
        position.longitude < 25 ||
        position.longitude > 46) {
      return null;
    }
    return LatLng(position.latitude, position.longitude);
  }

  void _setDefaultLocation(_LocationState state) {
    if (!mounted) return;
    setState(() => _locationState = state);
  }

  Future<void> _fetchStationsForRegion(
    LatLng center, {
    double maxDistMeters = 20000,
    int? maxResults,
  }) async {
    final requestId = ++_stationFetchSerial;
    if (mounted && !_isLoading) {
      setState(() => _isFetchingStations = true);
    }
    final data = await SupabaseService.fetchStations(
      latitude: center.latitude,
      longitude: center.longitude,
      maxDistMeters: maxDistMeters,
      maxResults: maxResults ?? _maxResultsForZoom(_currentZoom),
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
    return _stationsWithFuel(fuelType).where((station) {
      if (_selectedBrands.isNotEmpty &&
          !_selectedBrands.contains(station.brand)) {
        return false;
      }
      return true;
    }).toList(growable: false);
  }

  List<Station> _stationsWithFuel(String fuelType) {
    return _stations
        .where((station) => station.priceValueFor(fuelType) != null)
        .toList(growable: false);
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

    if (zoom < 11.9 && displayStations.length > 25) {
      final clusters = _clustersForZoom(
        stations: displayStations,
        fuelType: selectedFuel,
        zoom: zoom,
      );
      for (final cluster in clusters) {
        if (cluster.stations.length == 1) {
          markerFutures.add(_stationMarkerFor(
            station: cluster.stations.first,
            selectedFuel: selectedFuel,
            smartResult: smartResult,
            nearestStationId: nearestStationId,
            compact: true,
          ));
        } else {
          markerFutures.add(_clusterMarkerFor(
            cluster: cluster,
            selectedFuel: selectedFuel,
            zoom: zoom,
          ));
        }
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
    setState(() {
      _markers = markerList.toSet();
      _renderedZoomBucket = _markerZoomBucket(zoom);
    });
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
    final priceStr = station.priceTextFor(selectedFuel);
    final hasPrice = priceNum != null;
    final stationId = station.id.isNotEmpty
        ? station.id
        : '${station.brand}-$latitude-$longitude';
    final isCheapest = hasPrice &&
        (_focusMode == _MapFocusMode.cheapest ||
            _focusMode == _MapFocusMode.smart) &&
        stationId == smartResult?.cheapestStationId;
    final isMostLogical = hasPrice &&
        ((_focusMode == _MapFocusMode.smart &&
                stationId == smartResult?.mostLogicalStationId) ||
            (_focusMode == _MapFocusMode.nearest &&
                stationId == nearestStationId));
    final icon = await MarkerIconFactory.stationPrice(
      brand: station.brand,
      priceText: formatMarkerPrice(priceStr),
      hasPrice: hasPrice,
      isCheapest: isCheapest,
      isMostLogical: isMostLogical,
      compact: compact,
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

    final config = _declutterConfigForZoom(zoom);
    final byCell = <String, _StationCandidate>{};

    for (final station in stations) {
      final latitude = station.latitude;
      final longitude = station.longitude;
      if (latitude == null || longitude == null) continue;

      final latCell = (latitude / config.cellDegrees).floor();
      final lngCell = (longitude / config.cellDegrees).floor();
      final key = '$latCell:$lngCell';
      final price = station.priceValueFor(fuelType);
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
    if (_focusMode == _MapFocusMode.nearest) return distanceKm;
    if (price == null) return 10000 + distanceKm;
    if (_focusMode == _MapFocusMode.cheapest) return price;
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

  Widget _buildFuelSelector(UserPreferencesProvider prefs) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(4),
      decoration: _floatingPillDecoration(radius: 25),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: ['Kursunsuz 95', 'Motorin', 'LPG'].map((fuel) {
          final isActive = prefs.selectedFuel == fuel;
          return GestureDetector(
            onTap: () {
              prefs.updateSelectedFuel(fuel);
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 20),
              decoration: BoxDecoration(
                color: isActive ? const Color(0xFFFF5A5F) : Colors.transparent,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                fuel == 'Kursunsuz 95' ? 'Benzin' : fuel,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: isActive ? Colors.white : const Color(0xFF666666),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildGarageButton() {
    return GestureDetector(
      onTap: () => GarageModal.show(context),
      child: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          color: const Color(0xFF111827),
          shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFF10B981), width: 1.6),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF10B981).withOpacity(0.35),
              offset: const Offset(0, 5),
              blurRadius: 12,
            ),
          ],
        ),
        child: const Center(
          child: Icon(
            Icons.directions_car_rounded,
            color: Colors.white,
            size: 23,
          ),
        ),
      ),
    );
  }

  Widget _buildDrivingButton() {
    final isActive = _drivingModeEnabled;
    return GestureDetector(
      onTap: _toggleDrivingMode,
      child: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          color: isActive ? const Color(0xFF10B981) : Colors.white,
          shape: BoxShape.circle,
          border: Border.all(
            color: isActive ? const Color(0xFF047857) : const Color(0xFFE5E7EB),
            width: 1.4,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.14),
              offset: const Offset(0, 5),
              blurRadius: 12,
            ),
          ],
        ),
        child: Center(
          child: _isStartingDrivingMode
              ? SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.4,
                    color: isActive ? Colors.white : const Color(0xFF10B981),
                  ),
                )
              : Icon(
                  Icons.navigation_rounded,
                  color: isActive ? Colors.white : const Color(0xFF111827),
                  size: 24,
                ),
        ),
      ),
    );
  }

  Widget _buildSearchButton() {
    return GestureDetector(
      onTap: _showStationSearch,
      child: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFFE5E7EB), width: 1.4),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.14),
              offset: const Offset(0, 5),
              blurRadius: 12,
            ),
          ],
        ),
        child: const Center(
          child: Icon(
            Icons.search_rounded,
            color: Color(0xFF111827),
            size: 25,
          ),
        ),
      ),
    );
  }

  Widget _buildMapControlsButton() {
    final activeCount = _activeControlCount;
    final isActive = activeCount > 0;
    return GestureDetector(
      onTap: _showMapControls,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: isActive ? const Color(0xFF111827) : Colors.white,
              shape: BoxShape.circle,
              border: Border.all(
                color: isActive
                    ? const Color(0xFF10B981)
                    : const Color(0xFFE5E7EB),
                width: 1.4,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.14),
                  offset: const Offset(0, 5),
                  blurRadius: 12,
                ),
              ],
            ),
            child: Icon(
              Icons.tune_rounded,
              color: isActive ? Colors.white : const Color(0xFF111827),
              size: 24,
            ),
          ),
          if (isActive)
            Positioned(
              right: -2,
              top: -2,
              child: Container(
                width: 18,
                height: 18,
                decoration: BoxDecoration(
                  color: const Color(0xFFFF5A5F),
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
                alignment: Alignment.center,
                child: Text(
                  activeCount.toString(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 9,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  BoxDecoration _floatingPillDecoration({required double radius}) {
    return BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(radius),
      boxShadow: [
        BoxShadow(
          color: Colors.black.withOpacity(0.15),
          offset: const Offset(0, 4),
          blurRadius: 10,
        ),
      ],
    );
  }

  int get _activeControlCount {
    var count = 0;
    if (_focusMode != _MapFocusMode.smart) count += 1;
    if (_selectedBrands.isNotEmpty) count += 1;
    return count;
  }

  String? get _statusMessage {
    if (_stationLoadError != null) return _stationLoadError;
    if (_drivingError != null) return _drivingError;
    switch (_locationState) {
      case _LocationState.serviceOff:
        return 'Konum kapalı, İstanbul çevresi gösteriliyor.';
      case _LocationState.denied:
        return 'Konum izni yok, İstanbul çevresi gösteriliyor.';
      case _LocationState.fallback:
        return 'Konum alınamadı, İstanbul çevresi gösteriliyor.';
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
    );
  }

  void _setFocusMode(_MapFocusMode mode) {
    if (_focusMode == mode) return;
    setState(() {
      _focusMode = mode;
      _visibleStation = null;
    });
    _updateCalculationsAndMarkers(forceMarkerRefresh: true);
  }

  void _toggleBrandFilter(String brand) {
    setState(() {
      if (_selectedBrands.isEmpty) {
        _selectedBrands = {brand};
      } else if (_selectedBrands.contains(brand)) {
        _selectedBrands = {..._selectedBrands}..remove(brand);
        if (_selectedBrands.isEmpty) _selectedBrands = {};
      } else {
        _selectedBrands = {..._selectedBrands, brand};
      }
      _visibleStation = null;
    });
    _updateCalculationsAndMarkers(forceMarkerRefresh: true);
  }

  void _clearBrandFilters() {
    if (_selectedBrands.isEmpty) return;
    setState(() {
      _selectedBrands = {};
      _visibleStation = null;
    });
    _updateCalculationsAndMarkers(forceMarkerRefresh: true);
  }

  String _modeLabel(_MapFocusMode mode) {
    switch (mode) {
      case _MapFocusMode.smart:
        return 'Mantıklı';
      case _MapFocusMode.cheapest:
        return 'Ucuz';
      case _MapFocusMode.nearest:
        return 'Yakın';
    }
  }

  IconData _modeIcon(_MapFocusMode mode) {
    switch (mode) {
      case _MapFocusMode.smart:
        return Icons.auto_awesome_rounded;
      case _MapFocusMode.cheapest:
        return Icons.savings_rounded;
      case _MapFocusMode.nearest:
        return Icons.near_me_rounded;
    }
  }

  String _brandShortName(String brand) {
    switch (brand) {
      case 'Petrol Ofisi':
        return 'PO';
      case 'TotalEnergies':
        return 'Total';
      case 'Türkiye Petrolleri':
        return 'TP';
      default:
        return brand;
    }
  }

  Color _brandColor(String brand) {
    switch (brand) {
      case 'Shell':
        return const Color(0xFFD6001C);
      case 'Opet':
        return const Color(0xFF004797);
      case 'Petrol Ofisi':
        return const Color(0xFFDF1B25);
      case 'BP':
        return const Color(0xFF009900);
      case 'TotalEnergies':
        return const Color(0xFFED0000);
      case 'Türkiye Petrolleri':
        return const Color(0xFF111827);
      case 'Aytemiz':
        return const Color(0xFF00A0DF);
      default:
        return const Color(0xFF6B7280);
    }
  }

  void _showMapControls() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) {
          void refreshSheet() => setSheetState(() {});
          return _MapControlsSheet(
            focusMode: _focusMode,
            selectedBrands: _selectedBrands,
            brandOrder: _brandOrder,
            news: _news,
            modeLabel: _modeLabel,
            modeIcon: _modeIcon,
            brandShortName: _brandShortName,
            brandColor: _brandColor,
            onModeChanged: (mode) {
              _setFocusMode(mode);
              refreshSheet();
            },
            onBrandToggled: (brand) {
              _toggleBrandFilter(brand);
              refreshSheet();
            },
            onClearBrands: () {
              _clearBrandFilters();
              refreshSheet();
            },
            onNewsTap: _openNews,
            onPrivacyTap: _showPrivacyInfo,
          );
        },
      ),
    );
  }

  void _showPrivacyInfo() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => const _PrivacyInfoSheet(),
    );
  }

  Future<void> _openNews(NewsItem news) async {
    final uri = Uri.tryParse(news.link);
    if (uri == null) return;
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (e) {
      debugPrint('Could not launch $uri');
    }
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
        onStationSelected: (station) {
          _selectStation(station, animate: true);
        },
      ),
    );
  }

  void _selectStation(Station station, {bool animate = false}) {
    if (station.id.isNotEmpty) {
      unawaited(
          context.read<UserPreferencesProvider>().rememberStation(station.id));
    }
    setState(() {
      _visibleStation = station;
    });
    if (!animate) return;

    final latitude = station.latitude;
    final longitude = station.longitude;
    if (latitude == null || longitude == null) return;
    _mapController?.animateCamera(
      CameraUpdate.newCameraPosition(
        CameraPosition(
          target: LatLng(latitude, longitude),
          zoom: 14.2,
        ),
      ),
    );
  }

  Widget _buildEmptyState(UserPreferencesProvider prefs) {
    final hasBrandFilter = _selectedBrands.isNotEmpty;
    final hasError = _stationLoadError != null;
    final title = hasError
        ? 'Veri alınamadı'
        : hasBrandFilter
            ? 'Bu filtrede istasyon yok'
            : 'Bu bölgede fiyat bulunamadı';
    final description = hasError
        ? 'Bağlantıyı kontrol edip tekrar deneyebilirsin.'
        : hasBrandFilter
            ? 'Seçili marka filtresini temizleyip yeniden bakabilirsin.'
            : '${prefs.selectedFuel == 'Kursunsuz 95' ? 'Benzin' : prefs.selectedFuel} için doğrulanmış fiyat verisi görünmüyor.';
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
          GoogleMap(
            initialCameraPosition:
                CameraPosition(target: _currentLocation, zoom: 12),
            myLocationEnabled: true,
            myLocationButtonEnabled: true,
            markers: _markers,
            onMapCreated: (controller) => _mapController = controller,
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
            onTap: (_) => setState(() => _visibleStation = null),
            onCameraIdle: () async {
              if (_mapController == null) return;
              _scheduleMarkerRefresh(force: true);

              final bounds = await _mapController!.getVisibleRegion();
              final center = LatLng(
                  (bounds.northeast.latitude + bounds.southwest.latitude) / 2,
                  (bounds.northeast.longitude + bounds.southwest.longitude) /
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
              _fetchDebouncer = Timer(const Duration(milliseconds: 450), () {
                _fetchStationsForRegion(
                  center,
                  maxDistMeters: maxDistMeters,
                  maxResults: maxResults,
                );
              });
            },
          ),

          Positioned(
            top: MediaQuery.of(context).padding.top + 10,
            left: 0,
            right: 0,
            child: Column(
              children: [
                Center(child: _buildFuelSelector(prefs)),
                if (_statusMessage != null) ...[
                  const SizedBox(height: 10),
                  _buildStatusBanner(),
                ],
                if (_drivingModeEnabled) ...[
                  const SizedBox(height: 10),
                  _buildDrivingBanner(prefs),
                ],
                if (_isFetchingStations) ...[
                  const SizedBox(height: 8),
                  Container(
                    width: 92,
                    height: 4,
                    clipBehavior: Clip.hardEdge,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.7),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const LinearProgressIndicator(
                      backgroundColor: Colors.transparent,
                      color: Color(0xFFFF5A5F),
                    ),
                  ),
                ],
              ],
            ),
          ),

          Positioned(
            left: 18,
            bottom: 104,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildSearchButton(),
                const SizedBox(height: 12),
                _buildMapControlsButton(),
                const SizedBox(height: 12),
                _buildDrivingButton(),
                const SizedBox(height: 12),
                _buildGarageButton(),
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

          // Animated Bottom Sheet Overlay
          AnimatedPositioned(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            bottom: _visibleStation != null ? 0 : -500, // Slide up/down
            left: 0, right: 0,
            child: StationBottomSheet(
              visibleStation: _visibleStation,
              location: _currentLocation,
              closeSheet: () => setState(() => _visibleStation = null),
              selectedFuel: prefs.selectedFuel,
              isFavorite: _visibleStation != null &&
                  prefs.isFavoriteStation(_visibleStation!.id),
              onFavoriteToggle: () {
                final station = _visibleStation;
                if (station != null) {
                  prefs.toggleFavoriteStation(station.id);
                }
              },
              financialMessage: _visibleStation != null && _smartResult != null
                  ? SmartStationService.getFinancialMessage(
                      station: _visibleStation!,
                      location: _currentLocation,
                      stations: _filteredStations(fuelType: prefs.selectedFuel),
                      selectedFuel: prefs.selectedFuel,
                      tankCapacity: prefs.tankCapacity,
                      fuelConsumption: prefs.fuelConsumption,
                      result: _smartResult!,
                    )
                  : null,
            ),
          )
        ],
      ),
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

class _MapControlsSheet extends StatelessWidget {
  final _MapFocusMode focusMode;
  final Set<String> selectedBrands;
  final List<String> brandOrder;
  final List<NewsItem> news;
  final String Function(_MapFocusMode mode) modeLabel;
  final IconData Function(_MapFocusMode mode) modeIcon;
  final String Function(String brand) brandShortName;
  final Color Function(String brand) brandColor;
  final ValueChanged<_MapFocusMode> onModeChanged;
  final ValueChanged<String> onBrandToggled;
  final VoidCallback onClearBrands;
  final ValueChanged<NewsItem> onNewsTap;
  final VoidCallback onPrivacyTap;

  const _MapControlsSheet({
    required this.focusMode,
    required this.selectedBrands,
    required this.brandOrder,
    required this.news,
    required this.modeLabel,
    required this.modeIcon,
    required this.brandShortName,
    required this.brandColor,
    required this.onModeChanged,
    required this.onBrandToggled,
    required this.onClearBrands,
    required this.onNewsTap,
    required this.onPrivacyTap,
  });

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).padding.bottom;
    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.78,
      ),
      padding: EdgeInsets.fromLTRB(20, 14, 20, 18 + bottomInset),
      decoration: const BoxDecoration(
        color: Color(0xFFF9FAFB),
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(26),
          topRight: Radius.circular(26),
        ),
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Center(
              child: Container(
                width: 44,
                height: 5,
                decoration: BoxDecoration(
                  color: const Color(0xFFD1D5DB),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Harita ayarları',
                    style: TextStyle(
                      color: Color(0xFF111827),
                      fontWeight: FontWeight.w900,
                      fontSize: 22,
                    ),
                  ),
                ),
                GestureDetector(
                  onTap: () => Navigator.pop(context),
                  child: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0xFFE5E7EB)),
                    ),
                    child: const Icon(Icons.close_rounded),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            _sectionTitle('Sıralama'),
            const SizedBox(height: 10),
            Row(
              children: [
                for (final mode in _MapFocusMode.values) ...[
                  Expanded(child: _modeButton(mode)),
                  if (mode != _MapFocusMode.values.last)
                    const SizedBox(width: 8),
                ],
              ],
            ),
            const SizedBox(height: 22),
            Row(
              children: [
                Expanded(child: _sectionTitle('Markalar')),
                if (selectedBrands.isNotEmpty)
                  GestureDetector(
                    onTap: onClearBrands,
                    child: const Text(
                      'Temizle',
                      style: TextStyle(
                        color: Color(0xFFFF5A5F),
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _brandButton(
                  label: 'Tümü',
                  color: const Color(0xFF111827),
                  selected: selectedBrands.isEmpty,
                  onTap: onClearBrands,
                ),
                for (final brand in brandOrder)
                  _brandButton(
                    label: brandShortName(brand),
                    color: brandColor(brand),
                    selected: selectedBrands.contains(brand),
                    muted: selectedBrands.isNotEmpty &&
                        !selectedBrands.contains(brand),
                    onTap: () => onBrandToggled(brand),
                  ),
              ],
            ),
            if (news.isNotEmpty) ...[
              const SizedBox(height: 24),
              _sectionTitle('Piyasa haberleri'),
              const SizedBox(height: 10),
              for (final item in news.take(4)) _newsRow(item),
            ],
            const SizedBox(height: 8),
            GestureDetector(
              onTap: onPrivacyTap,
              child: Container(
                width: double.infinity,
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFFE5E7EB)),
                ),
                child: const Row(
                  children: [
                    Icon(
                      Icons.privacy_tip_outlined,
                      color: Color(0xFF6B7280),
                      size: 18,
                    ),
                    SizedBox(width: 9),
                    Expanded(
                      child: Text(
                        'Gizlilik ve veri kullanımı',
                        style: TextStyle(
                          color: Color(0xFF374151),
                          fontWeight: FontWeight.w900,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    Icon(
                      Icons.chevron_right_rounded,
                      color: Color(0xFF9CA3AF),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionTitle(String text) {
    return Text(
      text,
      style: const TextStyle(
        color: Color(0xFF6B7280),
        fontWeight: FontWeight.w900,
        fontSize: 12,
      ),
    );
  }

  Widget _modeButton(_MapFocusMode mode) {
    final selected = focusMode == mode;
    return GestureDetector(
      onTap: () => onModeChanged(mode),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        height: 48,
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF111827) : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? const Color(0xFF111827) : const Color(0xFFE5E7EB),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              modeIcon(mode),
              color: selected ? Colors.white : const Color(0xFF4B5563),
              size: 18,
            ),
            const SizedBox(width: 7),
            Flexible(
              child: Text(
                modeLabel(mode),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: selected ? Colors.white : const Color(0xFF374151),
                  fontWeight: FontWeight.w900,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _brandButton({
    required String label,
    required Color color,
    required bool selected,
    required VoidCallback onTap,
    bool muted = false,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? Colors.white : const Color(0xFFF3F4F6),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: muted ? const Color(0xFFE5E7EB) : color.withOpacity(0.75),
            width: selected ? 1.6 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: muted ? const Color(0xFFD1D5DB) : color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 7),
            Text(
              label,
              style: TextStyle(
                color:
                    muted ? const Color(0xFF9CA3AF) : const Color(0xFF111827),
                fontSize: 12,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _newsRow(NewsItem item) {
    return GestureDetector(
      onTap: () => onNewsTap(item),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: const Color(0xFFFFF1F2),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                Icons.article_rounded,
                color: Color(0xFFFF5A5F),
                size: 18,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF111827),
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    item.source,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Color(0xFF6B7280),
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Icon(
              Icons.open_in_new_rounded,
              color: Color(0xFF9CA3AF),
              size: 17,
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

class _PrivacyInfoSheet extends StatelessWidget {
  const _PrivacyInfoSheet();

  Future<void> _openPrivacyPolicy(BuildContext context) async {
    try {
      await launchUrl(
        _MapScreenState._privacyPolicyUri,
        mode: LaunchMode.externalApplication,
      );
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Gizlilik politikası açılamadı.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).padding.bottom;
    return Container(
      padding: EdgeInsets.fromLTRB(20, 14, 20, 18 + bottomInset),
      decoration: const BoxDecoration(
        color: Color(0xFFF9FAFB),
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(26),
          topRight: Radius.circular(26),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 44,
              height: 5,
              decoration: BoxDecoration(
                color: const Color(0xFFD1D5DB),
                borderRadius: BorderRadius.circular(999),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Gizlilik',
                  style: TextStyle(
                    color: Color(0xFF111827),
                    fontWeight: FontWeight.w900,
                    fontSize: 22,
                  ),
                ),
              ),
              GestureDetector(
                onTap: () => Navigator.pop(context),
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFE5E7EB)),
                  ),
                  child: const Icon(Icons.close_rounded),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _privacyRow(
            icon: Icons.my_location_rounded,
            title: 'Konum',
            text:
                'Yakındaki istasyonları bulmak ve mesafe hesaplamak için kullanılır. Konum geçmişi tutulmaz.',
          ),
          _privacyRow(
            icon: Icons.storage_rounded,
            title: 'Uygulama hafızası',
            text:
                'Seçili yakıt, araç bilgisi, favori ve son bakılan istasyonlar cihazda saklanır.',
          ),
          _privacyRow(
            icon: Icons.cloud_done_rounded,
            title: 'Canlı veri',
            text:
                'Fiyat ve istasyon verileri Supabase üzerinden okunur. Uygulama kullanıcı hesabı istemez.',
          ),
          const SizedBox(height: 8),
          const Text(
            'Detaylı gizlilik politikası GitHub Pages üzerinde herkese açık olarak yayınlanır ve Play Console için kullanılabilir.',
            style: TextStyle(
              color: Color(0xFF6B7280),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton.icon(
              onPressed: () => _openPrivacyPolicy(context),
              icon: const Icon(Icons.open_in_new_rounded, size: 18),
              label: const Text('Gizlilik politikasını aç'),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF111827),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _privacyRow({
    required IconData icon,
    required String title,
    required String text,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: const Color(0xFFEFF6FF),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: const Color(0xFF2563EB), size: 18),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFF111827),
                    fontSize: 13,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  text,
                  style: const TextStyle(
                    color: Color(0xFF6B7280),
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
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
      final price = station.priceValueFor(fuelType);
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
  final ValueChanged<Station> onStationSelected;

  const _StationSearchSheet({
    required this.stationsFuture,
    required this.location,
    required this.selectedFuel,
    required this.selectedBrands,
    required this.favoriteStationIds,
    required this.recentStationIds,
    required this.onStationSelected,
  });

  @override
  State<_StationSearchSheet> createState() => _StationSearchSheetState();
}

class _StationSearchSheetState extends State<_StationSearchSheet> {
  final TextEditingController _controller = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: Container(
        height: MediaQuery.of(context).size.height * 0.72,
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 18),
        decoration: const BoxDecoration(
          color: Color(0xFFF9FAFB),
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(26),
            topRight: Radius.circular(26),
          ),
        ),
        child: Column(
          children: [
            Container(
              width: 44,
              height: 5,
              decoration: BoxDecoration(
                color: const Color(0xFFD1D5DB),
                borderRadius: BorderRadius.circular(999),
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: const Color(0xFFE5E7EB)),
                    ),
                    child: TextField(
                      controller: _controller,
                      autofocus: true,
                      textInputAction: TextInputAction.search,
                      onChanged: (value) => setState(() => _query = value),
                      decoration: const InputDecoration(
                        hintText: 'İstasyon, marka, il veya ilçe ara',
                        prefixIcon: Icon(Icons.search_rounded),
                        border: InputBorder.none,
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 14, vertical: 14),
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
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFFE5E7EB)),
                    ),
                    child: const Icon(Icons.close_rounded),
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
                          CircularProgressIndicator(color: Color(0xFFFF5A5F)),
                    );
                  }
                  final stations = snapshot.data ?? const <Station>[];
                  final results = _searchResults(stations);
                  if (results.isEmpty) {
                    return const Center(
                      child: Text(
                        'Sonuç bulunamadı',
                        style: TextStyle(
                          color: Color(0xFF6B7280),
                          fontWeight: FontWeight.w700,
                        ),
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
    final filtered = stations.where((station) {
      if (widget.selectedBrands.isNotEmpty &&
          !widget.selectedBrands.contains(station.brand)) {
        return false;
      }
      if (station.priceValueFor(widget.selectedFuel) == null) return false;
      if (query.isEmpty) return true;
      final haystack = _normalize(
        '${station.brand} ${station.displayName} ${station.city} ${station.district}',
      );
      return haystack.contains(query);
    }).map((station) {
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

    filtered.sort((a, b) {
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
      final aDistance = a.distanceKm ?? 999999;
      final bDistance = b.distanceKm ?? 999999;
      final distanceCompare = aDistance.compareTo(bDistance);
      if (distanceCompare != 0) return distanceCompare;
      return a.station.displayName.compareTo(b.station.displayName);
    });

    return filtered.take(35).toList(growable: false);
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
                  style: const TextStyle(
                    color: Color(0xFFFF5A5F),
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
