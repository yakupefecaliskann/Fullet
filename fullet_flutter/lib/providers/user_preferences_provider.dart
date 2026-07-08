import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/notification_service.dart';
import '../services/supabase_service.dart';

class UserPreferencesProvider extends ChangeNotifier {
  double tankCapacity = 50.0;
  double fuelConsumption = 7.0;
  String selectedFuel = 'Kursunsuz 95';
  String? selectedMake;
  String? selectedModel;
  Set<String> favoriteStationIds = {};
  List<String> recentStationIds = [];

  bool _isLoaded = false;
  bool get isLoaded => _isLoaded;
  bool get hasVehicle => selectedMake != null && selectedModel != null;

  final Completer<void> _readyCompleter = Completer<void>();
  Future<void> get ready => _readyCompleter.future;

  UserPreferencesProvider() {
    _loadPreferences();
  }

  Future<void> _loadPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    tankCapacity = prefs.getDouble('tankCapacity') ?? 50.0;
    fuelConsumption = prefs.getDouble('fuelConsumption') ?? 7.0;
    selectedFuel = prefs.getString('defaultFuel') ?? 'Kursunsuz 95';
    selectedMake = prefs.getString('selectedMake');
    selectedModel = prefs.getString('selectedModel');
    favoriteStationIds =
        (prefs.getStringList('favoriteStationIds') ?? const []).toSet();
    recentStationIds = prefs.getStringList('recentStationIds') ?? const [];
    _isLoaded = true;
    if (!_readyCompleter.isCompleted) _readyCompleter.complete();
    notifyListeners();
  }

  Future<void> updateTankCapacity(double val) async {
    tankCapacity = val;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('tankCapacity', val);
    notifyListeners();
  }

  Future<void> updateFuelConsumption(double val) async {
    fuelConsumption = val;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('fuelConsumption', val);
    notifyListeners();
  }

  Future<void> updateSelectedFuel(String fuel) async {
    selectedFuel = fuel;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('defaultFuel', fuel);
    notifyListeners();
  }

  // Anlık güncelleme (chip bar için) — arka planda kaydeder
  void setSelectedFuel(String fuel) {
    selectedFuel = fuel;
    notifyListeners();
    SharedPreferences.getInstance()
        .then((p) => p.setString('defaultFuel', fuel));
  }

  Future<void> updateCarSelection(String make, String? model,
      {double? tank, double? cons, String? fuel}) async {
    selectedMake = make;
    selectedModel = model;
    await NotificationService.cancelGarageReminder();

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('selectedMake', make);
    if (model != null) {
      await prefs.setString('selectedModel', model);
    } else {
      await prefs.remove('selectedModel');
    }

    if (tank != null) {
      tankCapacity = tank;
      await prefs.setDouble('tankCapacity', tank);
    }
    if (cons != null) {
      fuelConsumption = cons;
      await prefs.setDouble('fuelConsumption', cons);
    }
    if (fuel != null) {
      selectedFuel = fuel;
      await prefs.setString('defaultFuel', fuel);
    }

    notifyListeners();
  }

  bool isFavoriteStation(String stationId) {
    return stationId.isNotEmpty && favoriteStationIds.contains(stationId);
  }

  Future<void> toggleFavoriteStation(String stationId) async {
    if (stationId.isEmpty) return;
    final next = {...favoriteStationIds};
    final adding = !next.contains(stationId);
    if (adding) {
      next.add(stationId);
    } else {
      next.remove(stationId);
    }
    favoriteStationIds = next;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('favoriteStationIds', favoriteStationIds.toList());
    notifyListeners();

    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid != null) {
      if (adding) {
        SupabaseService.addFavorite(uid, stationId);
      } else {
        SupabaseService.removeFavorite(uid, stationId);
      }
    }
  }

  Future<void> mergeRemoteFavorites(Set<String> remoteIds) async {
    final merged = {...favoriteStationIds, ...remoteIds};
    if (merged.length == favoriteStationIds.length) return;
    favoriteStationIds = merged;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('favoriteStationIds', merged.toList());
    notifyListeners();
  }

  Future<void> rememberStation(String stationId) async {
    if (stationId.isEmpty) return;
    final next = [
      stationId,
      ...recentStationIds.where((id) => id != stationId),
    ].take(12).toList(growable: false);
    recentStationIds = next;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('recentStationIds', recentStationIds);
    notifyListeners();
  }

  Future<void> clearVehicle() async {
    selectedMake = null;
    selectedModel = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('selectedMake');
    await prefs.remove('selectedModel');
    notifyListeners();
  }
}
