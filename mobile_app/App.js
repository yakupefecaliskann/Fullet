import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, View, Dimensions, Text, ActivityIndicator, TouchableOpacity, Platform, Linking, LayoutAnimation, UIManager, Animated, Image, Easing } from 'react-native';
import MapView, { Marker } from 'react-native-maps';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}
import * as Location from 'expo-location';
import { supabase } from './utils/supabase';
import { StatusBar } from 'expo-status-bar';

const deg2rad = (deg) => deg * (Math.PI / 180);

const getDistanceKm = (lat1, lon1, lat2, lon2) => {
  if (!lat1 || !lon1 || !lat2 || !lon2) return null;
  const R = 6371; // Dunyanin yaricapi (KM)
  const dLat = deg2rad(parseFloat(lat2) - parseFloat(lat1));  
  const dLon = deg2rad(parseFloat(lon2) - parseFloat(lon1)); 
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(deg2rad(parseFloat(lat1))) * Math.cos(deg2rad(parseFloat(lat2))) * 
    Math.sin(dLon/2) * Math.sin(dLon/2); 
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)); 
  return R * c; // KM cinsinden Mesafe
};

const MarqueeBanner = ({ news }) => {
  const animatedValue = useRef(new Animated.Value(Dimensions.get('window').width)).current;
  
  // Metnin toplam uzunluğunu yaklaşık olarak hesapla ki animasyon süresini ve bitiş noktasını bilelim
  const fullTextLength = news.reduce((acc, curr) => acc + (curr.baslik || '').length + (curr.kaynak || '').length + 15, 0);

  useEffect(() => {
    if (news.length === 0) return;
    const duration = fullTextLength * 80; 
    const animate = () => {
      animatedValue.setValue(Dimensions.get('window').width);
      Animated.timing(animatedValue, {
        toValue: -fullTextLength * 8.5, 
        duration: duration,
        easing: Easing.linear,
        useNativeDriver: true,
      }).start(() => animate());
    };
    animate();
  }, [news, fullTextLength]);

  if (!news || news.length === 0) return null;

  return (
    <View style={styles.marqueeContainer}>
      <View style={styles.marqueeLabelBox}>
        <Text style={styles.marqueeLabelText}>SONDAKİKA</Text>
      </View>
      <View style={styles.marqueeTrack}>
        <Animated.View style={{ flexDirection: 'row', transform: [{ translateX: animatedValue }] }}>
          {news.map((n, i) => (
            <TouchableOpacity 
              key={i} 
              activeOpacity={0.6}
              onPress={() => Linking.openURL(n.link).catch(err => console.error("Link acilamadi:", err))}
            >
              <Text style={styles.marqueeText}>🔴 {n.baslik} [{n.kaynak}]   |   </Text>
            </TouchableOpacity>
          ))}
        </Animated.View>
      </View>
    </View>
  );
};

export default function App() {
  const [location, setLocation] = useState(null);
  const [stations, setStations] = useState([]);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFuel, setSelectedFuel] = useState('Kursunsuz 95');
  const [visibleStation, setVisibleStation] = useState(null);
  const slideAnim = useRef(new Animated.Value(500)).current;

  const openSheet = (station) => {
    if (visibleStation && visibleStation.id !== station.id) {
      // Baska bir istasyona tiklandiysa once eskisi kapansin, sonra yenisi acilsin
      Animated.timing(slideAnim, {
        toValue: 500,
        duration: 150,
        useNativeDriver: true,
      }).start(() => {
        setVisibleStation(station);
        Animated.spring(slideAnim, {
          toValue: 0,
          useNativeDriver: true,
          tension: 65,
          friction: 9,
        }).start();
      });
    } else {
      setVisibleStation(station);
      Animated.spring(slideAnim, {
        toValue: 0,
        useNativeDriver: true,
        tension: 65,
        friction: 9,
      }).start();
    }
  };

  const closeSheet = () => {
    Animated.timing(slideAnim, {
      toValue: 500,
      duration: 250,
      useNativeDriver: true,
    }).start(() => {
      setVisibleStation(null);
    });
  };

  const getLogoResource = (marka) => {
    switch (marka) {
      case 'Shell': return require('./assets/shell.png.png');
      case 'Opet': return require('./assets/opet.png.png');
      case 'Petrol Ofisi': return require('./assets/po.png.png');
      case 'BP': return require('./assets/bp.png.png');
      case 'TotalEnergies': return require('./assets/total.png.png');
      default: return require('./assets/icon.png');
    }
  };

  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        // Lokasyon izni verilmezse varsayilan olarak Istanbul Merkez'i goster
        setLocation({
          latitude: 41.0082,
          longitude: 28.9784,
          latitudeDelta: 0.1,
          longitudeDelta: 0.1,
        });
      } else {
        let loc = await Location.getCurrentPositionAsync({});
        setLocation({
          latitude: loc.coords.latitude,
          longitude: loc.coords.longitude,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        });
      }

      fetchStations();
      fetchNews();
    })();
  }, []);

  const fetchNews = async () => {
    try {
      const { data, error } = await supabase
        .from('haberler')
        .select('*')
        .order('tarih', { ascending: false })
        .limit(10);
        
      if (!error && data) {
        setNews(data);
      }
    } catch (err) {
      console.error('Haber Cekme Hatasi:', err);
    }
  };

  const fetchStations = async () => {
    try {
      // istasyonlar ve iliskili fiyatlari (fiyatlar tablosu) cekiyoruz
      const { data, error } = await supabase
        .from('istasyonlar')
        .select(`
          id, 
          marka, 
          isim, 
          il, 
          ilce, 
          enlem, 
          boylam,
          fiyatlar (yakit_tipi, fiyat),
          fiyat_gecmisi (yakit_tipi, fiyat_farki, degisim_tarihi)
        `)
        .not('enlem', 'is', null)
        .not('boylam', 'is', null);

      if (error) {
        console.error('Supabase Error:', error);
      } else {
        setStations(data || []);
      }
    } catch (err) {
      console.error('Fetch Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getPrice = (pricesArray, targetType) => {
    if (!pricesArray) return '-';
    const priceObj = pricesArray.find(p => p.yakit_tipi === targetType || p.yakit_tipi.includes(targetType));
    return priceObj ? priceObj.fiyat : '-';
  };

  const getTrendIcon = (station, targetType) => {
    if (!station.fiyat_gecmisi || station.fiyat_gecmisi.length === 0) return null;
    const history = station.fiyat_gecmisi.filter(h => h.yakit_tipi === targetType || h.yakit_tipi.includes(targetType));
    if (history.length > 0) {
      history.sort((a, b) => new Date(b.degisim_tarihi) - new Date(a.degisim_tarihi));
      const trendVal = history[0].fiyat_farki;
      if (trendVal < 0) return <Text style={{color: '#16a34a', fontWeight: 'bold', fontSize: 16, marginLeft: 6}}>↓</Text>;
      if (trendVal > 0) return <Text style={{color: '#dc2626', fontWeight: 'bold', fontSize: 16, marginLeft: 6}}>↑</Text>;
    }
    return null;
  };

  // Zeki Algoritma Hesaplamalari
  let cheapestStationId = null;
  let cheapestPrice = Infinity;
  let mostLogicalStationId = null;
  let bestTotalCost = Infinity;

  if (location && stations.length > 0) {
    stations.forEach(s => {
      const price = parseFloat(getPrice(s.fiyatlar, selectedFuel));
      if (!isNaN(price)) {
        if (price < cheapestPrice) {
          cheapestPrice = price;
          cheapestStationId = s.id;
        }

        const distance = getDistanceKm(location.latitude, location.longitude, s.enlem, s.boylam);
        if (distance !== null) {
          const costToFill = 50 * price;
          const travelCost = distance * 0.07 * price;
          const totalCost = costToFill + travelCost;

          if (totalCost < bestTotalCost) {
            bestTotalCost = totalCost;
            mostLogicalStationId = s.id;
          }
        }
      }
    });
  }

  const getFinancialMessage = (station) => {
    if (!location) return null;
    const price = parseFloat(getPrice(station.fiyatlar, selectedFuel));
    if (isNaN(price)) return null;

    const myDistance = getDistanceKm(location.latitude, location.longitude, station.enlem, station.boylam);
    if (myDistance === null) return null;

    const myTotalCost = (50 * price) + (myDistance * 0.07 * price);

    if (station.id === mostLogicalStationId) {
      if (cheapestStationId && cheapestStationId !== mostLogicalStationId) {
        const cheapSt = stations.find(s => s.id === cheapestStationId);
        if (cheapSt) {
          const cheapPrice = parseFloat(getPrice(cheapSt.fiyatlar, selectedFuel));
          const cheapDist = getDistanceKm(location.latitude, location.longitude, cheapSt.enlem, cheapSt.boylam);
          const cheapTotal = (50 * cheapPrice) + (cheapDist * 0.07 * cheapPrice);
          const saved = cheapTotal - myTotalCost;
          if (saved > 0) {
            return { type: 'success', text: `🏆 Hem Yakın Hem Kârlı!\nEn ucuza gitmeye kıyasla net ${saved.toFixed(1)}₺ kazandırdı.` };
          }
        }
      }
      return { type: 'success', text: `🏆 En Mantıklı Seçim\nŞu an sizin için en hesaplı ve yakın istasyon.` };
    }

    if (station.id === cheapestStationId) {
      const loss = myTotalCost - bestTotalCost;
      return { type: 'danger', text: `⚠️ Tuzak İstasyon!\nPompa ucuz ama yol masrafıyla ${loss.toFixed(1)}₺ zarar edersiniz.` };
    }

    const loss = myTotalCost - bestTotalCost;
    return { type: 'warning', text: `📉 Daha Kârlısı Var!\nEn mantıklı yere kıyasla ${loss.toFixed(1)}₺ daha fazla masrafınız olur.` };
  };

  if (loading || !location) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#FF5A5F" />
        <Text style={styles.loadingText}>Harita Yükleniyor...</Text>
      </View>
    );
  }

  const openDirections = (lat, lng, name) => {
    const scheme = Platform.select({ ios: 'maps:0,0?q=', android: 'geo:0,0?q=' });
    const latLng = `${lat},${lng}`;
    const url = Platform.select({
      ios: `${scheme}${name}@${latLng}`,
      android: `${scheme}${latLng}(${name})`
    });
    
    Linking.openURL(url).catch(err => console.error("Navigasyon acilamadi:", err));
  };

  return (
    <View style={styles.container}>
      <StatusBar style="auto" />
      
      {/* Sondakika Marquee (Kayan Yazi) */}
      <MarqueeBanner news={news} />

      {/* Yakit Tipi Secici */}
      <View style={styles.fuelSelector}>
        {['Kursunsuz 95', 'Motorin', 'LPG'].map(fuel => (
          <TouchableOpacity 
            key={fuel}
            style={[styles.fuelButton, selectedFuel === fuel && styles.fuelButtonActive]}
            onPress={() => setSelectedFuel(fuel)}
          >
            <Text style={[styles.fuelButtonText, selectedFuel === fuel && styles.fuelButtonTextActive]}>
              {fuel === 'Kursunsuz 95' ? 'Benzin' : fuel}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <MapView 
        style={styles.map} 
        initialRegion={location}
        showsUserLocation={true}
        showsMyLocationButton={true}
        onPress={() => closeSheet()}
      >
        {stations.map((station) => {
          const priceStr = getPrice(station.fiyatlar, selectedFuel);
          const hasPrice = priceStr !== '-';
          const priceNum = parseFloat(priceStr);
          const isCheapest = (hasPrice && !isNaN(priceNum) && station.id === cheapestStationId);
          const isMostLogical = (hasPrice && !isNaN(priceNum) && station.id === mostLogicalStationId);
          
          let bgColor = '#333';
          let textColor = '#FFF';

          if (!hasPrice) {
            bgColor = '#E5E7EB'; 
            textColor = '#9CA3AF'; 
          } else {
            if (isMostLogical) bgColor = '#00B84F'; // Altin yildizli kazanana YESIL!
            else if (isCheapest) bgColor = '#EF4444'; // Tuzaksa veya sadece ucuzsa KIRMIZI uyarisi
            else if (station.marka === 'Shell') bgColor = '#FFCC00'; 
            else if (station.marka === 'Opet') bgColor = '#004797'; 
            else if (station.marka === 'Petrol Ofisi') bgColor = '#DF1B25'; 
            else if (station.marka === 'BP') bgColor = '#009900'; 
            else if (station.marka === 'TotalEnergies') bgColor = '#ED0000'; 

            textColor = (bgColor === '#FFCC00' || bgColor === '#fef9c3') ? '#D6001C' : '#FFF';
          }

          return (
            <Marker
              key={`${station.id}-${selectedFuel}`}
              coordinate={{
                latitude: parseFloat(station.enlem),
                longitude: parseFloat(station.boylam),
              }}
              opacity={hasPrice ? 1 : 0.65}
              onPress={(e) => {
                e.stopPropagation();
                openSheet(station);
              }}
            >
              <View style={[styles.customPin, { backgroundColor: bgColor, borderColor: hasPrice ? '#ffffff' : '#D1D5DB' }]}>
                <Text style={[styles.pinText, { color: textColor }]}>
                  {hasPrice ? `${priceStr} ₺` : 'Yok'}
                </Text>
              </View>
            </Marker>
          );
        })}
      </MapView>

      {/* Animated Bottom Sheet */}
      {visibleStation && (
        <Animated.View style={[styles.bottomSheet, { transform: [{ translateY: slideAnim }] }]}>
          <View>
            {/* Finansal Asistan Rozeti */}
            {(() => {
              const msg = getFinancialMessage(visibleStation);
              if (msg) {
                return (
                  <View style={[styles.financeBadge, msg.type === 'success' ? styles.badgeSuccess : msg.type === 'danger' ? styles.badgeDanger : styles.badgeWarning]}>
                    <Text style={[styles.financeText, msg.type === 'warning' && {color: '#854d0e'}, msg.type === 'danger' && {color: '#991b1b'}, msg.type === 'success' && {color: '#166534'}]}>
                      {msg.text}
                    </Text>
                  </View>
                );
              }
              return null;
            })()}

            <View style={styles.bottomSheetHeader}>
              <View style={{ flexDirection: 'row', alignItems: 'center', maxWidth: '85%' }}>
                <Image source={getLogoResource(visibleStation.marka)} style={styles.brandLogo} resizeMode="contain" />
                <View>
                  <Text style={styles.bottomBrand}>{visibleStation.marka}</Text>
                  <Text style={styles.bottomName}>{visibleStation.isim}</Text>
                  {location && visibleStation.enlem && visibleStation.boylam && (
                    <Text style={styles.distanceText}>
                      🚘 {(getDistanceKm(location.latitude, location.longitude, visibleStation.enlem, visibleStation.boylam)).toFixed(1)} KM Uzaklıkta
                    </Text>
                  )}
                </View>
              </View>
              <TouchableOpacity 
                onPress={() => closeSheet()} 
                style={styles.closeBtn}
              >
                <Text style={styles.closeBtnText}>✕</Text>
              </TouchableOpacity>
            </View>
          </View>
          
          <View style={styles.bottomPricesRow}>
            <View style={styles.priceBox}>
              <Text style={styles.priceBoxLabel}>Benzin</Text>
              <View style={{flexDirection: 'row', alignItems: 'center'}}>
                <Text style={[styles.priceBoxValue, getPrice(visibleStation.fiyatlar, 'Kursunsuz 95') === '-' && styles.priceBoxDisabled]}>
                  {getPrice(visibleStation.fiyatlar, 'Kursunsuz 95') === '-' ? 'Yok' : `${getPrice(visibleStation.fiyatlar, 'Kursunsuz 95')} ₺`}
                </Text>
                {getTrendIcon(visibleStation, 'Kursunsuz 95')}
              </View>
            </View>
            <View style={styles.priceBox}>
              <Text style={styles.priceBoxLabel}>Motorin</Text>
              <View style={{flexDirection: 'row', alignItems: 'center'}}>
                <Text style={[styles.priceBoxValue, getPrice(visibleStation.fiyatlar, 'Motorin') === '-' && styles.priceBoxDisabled]}>
                  {getPrice(visibleStation.fiyatlar, 'Motorin') === '-' ? 'Yok' : `${getPrice(visibleStation.fiyatlar, 'Motorin')} ₺`}
                </Text>
                {getTrendIcon(visibleStation, 'Motorin')}
              </View>
            </View>
            <View style={styles.priceBox}>
              <Text style={styles.priceBoxLabel}>LPG</Text>
              <View style={{flexDirection: 'row', alignItems: 'center'}}>
                <Text style={[styles.priceBoxValue, getPrice(visibleStation.fiyatlar, 'LPG') === '-' && styles.priceBoxDisabled]}>
                  {getPrice(visibleStation.fiyatlar, 'LPG') === '-' ? 'Yok' : `${getPrice(visibleStation.fiyatlar, 'LPG')} ₺`}
                </Text>
                {getTrendIcon(visibleStation, 'LPG')}
              </View>
            </View>
          </View>

          <TouchableOpacity 
            style={styles.bottomNavBtn} 
            activeOpacity={0.8}
            onPress={() => openDirections(visibleStation.enlem, visibleStation.boylam, visibleStation.isim)}
          >
            <Text style={styles.bottomNavBtnText}>📍 Yol Tarifi Al</Text>
          </TouchableOpacity>
        </Animated.View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
  },
  loadingText: {
    marginTop: 15,
    fontSize: 16,
    color: '#333',
    fontWeight: '500',
  },
  map: {
    width: Dimensions.get('window').width,
    height: Dimensions.get('window').height,
  },
  fuelSelector: {
    position: 'absolute',
    top: Platform.OS === 'ios' ? 110 : 85,
    alignSelf: 'center',
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 25,
    padding: 4,
    zIndex: 10,
    elevation: 8,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 10,
  },
  fuelButton: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 20,
  },
  fuelButtonActive: {
    backgroundColor: '#FF5A5F',
  },
  fuelButtonText: {
    fontWeight: '700',
    fontSize: 14,
    color: '#666',
  },
  fuelButtonTextActive: {
    color: 'white',
  },
  customPin: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: '#ffffff',
    elevation: 5,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 3,
  },
  pinText: {
    fontWeight: '900',
    fontSize: 13,
  },
  bottomSheet: {
    position: 'absolute',
    bottom: 0,
    width: '100%',
    backgroundColor: '#fff',
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    padding: 24,
    paddingBottom: Platform.OS === 'ios' ? 40 : 24,
    elevation: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -5 },
    shadowOpacity: 0.15,
    shadowRadius: 15,
    zIndex: 100,
  },
  bottomSheetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  bottomBrand: {
    fontSize: 22,
    fontWeight: '900',
    color: '#FF5A5F',
    marginBottom: 2,
  },
  bottomName: {
    fontSize: 12,
    color: '#666',
    lineHeight: 18,
  },
  distanceText: {
    fontSize: 12,
    fontWeight: '800',
    color: '#00B84F',
    marginTop: 4,
  },
  financeBadge: {
    padding: 10,
    borderRadius: 8,
    marginBottom: 16,
    width: '100%',
  },
  badgeSuccess: { backgroundColor: '#dcfce7' },
  badgeDanger: { backgroundColor: '#fee2e2' },
  badgeWarning: { backgroundColor: '#fef9c3' },
  financeText: {
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 18,
  },
  brandLogo: {
    width: 48,
    height: 48,
    marginRight: 16,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  closeBtn: {
    padding: 5,
    backgroundColor: '#F3F4F6',
    borderRadius: 20,
    width: 32,
    height: 32,
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeBtnText: {
    color: '#666',
    fontSize: 16,
    fontWeight: 'bold',
  },
  bottomPricesRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#F9FAFB',
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
  },
  priceBox: {
    alignItems: 'center',
    flex: 1,
  },
  priceBoxLabel: {
    fontSize: 12,
    color: '#9CA3AF',
    fontWeight: '600',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  priceBoxValue: {
    fontSize: 16,
    fontWeight: '800',
    color: '#1F2937',
  },
  priceBoxDisabled: {
    color: '#D1D5DB',
  },
  bottomNavBtn: {
    backgroundColor: '#00B84F',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    shadowColor: '#00B84F',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  bottomNavBtnText: {
    color: 'white',
    fontWeight: '800',
    fontSize: 16,
    letterSpacing: 0.5,
  },
  marqueeContainer: {
    position: 'absolute',
    top: Platform.OS === 'ios' ? 65 : 45, 
    width: '92%',
    alignSelf: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    zIndex: 99,
    elevation: 10,
    shadowColor: '#dc2626', 
    shadowOpacity: 0.8,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 15,
    overflow: 'hidden',
    height: 34,
    borderWidth: 1,
    borderColor: '#991b1b', 
  },
  marqueeLabelBox: {
    backgroundColor: '#dc2626', 
    paddingHorizontal: 8,
    height: '100%',
    justifyContent: 'center',
    zIndex: 2,
    borderTopLeftRadius: 7,
    borderBottomLeftRadius: 7,
  },
  marqueeLabelText: {
    color: '#fff',
    fontWeight: '900',
    fontSize: 11,
    letterSpacing: 0.5,
  },
  marqueeTrack: {
    flex: 1,
    overflow: 'hidden',
    justifyContent: 'center',
  },
  marqueeText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 13,
    width: 9999, // Tasmayi garantiye almak icin genis
  }
});


