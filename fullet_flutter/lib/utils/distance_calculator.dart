import 'dart:math' as math;

double deg2rad(double deg) => deg * (math.pi / 180);

double? getDistanceKm(double? lat1, double? lon1, double? lat2, double? lon2) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return null;
  const double R = 6371; // Earth radius in KM
  final double dLat = deg2rad(lat2 - lat1);
  final double dLon = deg2rad(lon2 - lon1);
  final double a = math.sin(dLat / 2) * math.sin(dLat / 2) +
      math.cos(deg2rad(lat1)) *
          math.cos(deg2rad(lat2)) *
          math.sin(dLon / 2) *
          math.sin(dLon / 2);
  final double c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  return R * c; // Distance in KM
}
