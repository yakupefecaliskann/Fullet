import React, { useState, useEffect, useRef, useMemo } from 'react';
import { StyleSheet, View, Dimensions, Text, ActivityIndicator, TouchableOpacity, Platform, Linking, LayoutAnimation, UIManager, Animated, Image, Easing, Modal, ScrollView, LogBox, StatusBar as RNStatusBar, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Device from 'expo-device';
import MapView from 'react-native-map-clustering';
import { Marker } from 'react-native-maps';
import * as Sentry from '@sentry/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { carDatabase } from './utils/carDatabase';

LogBox.ignoreLogs([
  'expo-notifications: Android Push notifications',
  '`expo-notifications` functionality is not fully supported',
  'LayoutAnimation'
]);

// Constants
import * as Location from 'expo-location';
import { supabase } from './utils/supabase';
import { StatusBar } from 'expo-status-bar';
import * as Notifications from 'expo-notifications';
import { registerForPushNotificationsAsync } from './utils/registerPush';
import * as WebBrowser from 'expo-web-browser';
import MarqueeBanner from './src/components/UI/MarqueeBanner';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const deg2rad = (deg) => deg * (Math.PI / 180);

const getLastPriceChangeText = (station) => {
  if (!station.fiyat_gecmisi || station.fiyat_gecmisi.length === 0) return "Yeni";
  const latest = [...station.fiyat_gecmisi].sort((a, b) => new Date(b.degisim_tarihi) - new Date(a.degisim_tarihi))[0];
  if (!latest || !latest.degisim_tarihi) return "Yeni";
  const diffHours = Math.round((new Date() - new Date(latest.degisim_tarihi)) / (1000 * 60 * 60));
  if (diffHours === 0) return "Güncel";
  if (diffHours < 24) return `${diffHours}s önce`;
  return `${Math.floor(diffHours / 24)}g önce`;
};

const getDistanceKm = (lat1, lon1, lat2, lon2) => {
  if (!lat1 || !lon1 || !lat2 || !lon2) return null;
  const R = 6371; // Dunyanin yaricapi (KM)
  const dLat = deg2rad(parseFloat(lat2) - parseFloat(lat1));  
  const dLon = deg2rad(parseFloat(lon2) - parseFloat(lon1)); 
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(deg2rad(parseFloat(lat1))) * Math.cos(deg2rad(parseFloat(lat2))) * 
    Math.sin(dLon/2) * Math.sin(dLon/2); 
  return R * c; // KM cinsinden Mesafe
};

Sentry.init({
  dsn: 'BURAYA_SENTRY_DSN_GELECEK', // TODO: Sentry.io panelinden alacağın DSN adresini buraya gir
  debug: false, 
  enableInExpoDevelopment: true,
  tracesSampleRate: 1.0, // Performans takibi
});

function App() {
  const [location, setLocation] = useState(null);
  const [stations, setStations] = useState([]);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFuel, setSelectedFuel] = useState('Kursunsuz 95');
  const [visibleStation, setVisibleStation] = useState(null);
  const [garageVisible, setGarageVisible] = useState(false);
  const [tankCapacity, setTankCapacity] = useState(50);
  const [fuelConsumption, setFuelConsumption] = useState(7.0);
  const [selectedMake, setSelectedMake] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [pickerMode, setPickerMode] = useState(null); 
  const slideAnim = useRef(new Animated.Value(500)).current;
  const garageFuelAnim = useRef(new Animated.Value(0)).current;
  const notificationListener = useRef();
  const responseListener = useRef();

  const smoothTransition = () => {
    LayoutAnimation.configureNext({
      duration: 300,
      create: { type: LayoutAnimation.Types.easeInEaseOut, property: LayoutAnimation.Properties.opacity },
      update: { type: LayoutAnimation.Types.easeInEaseOut }
    });
  };

  useEffect(() => {
    const idx = ['Kursunsuz 95', 'Motorin', 'LPG'].indexOf(selectedFuel);
    Animated.spring(garageFuelAnim, {
      toValue: idx >= 0 ? idx : 0,
      useNativeDriver: false,
      tension: 60,
      friction: 8,
    }).start();
  }, [selectedFuel]);

  const handleTankChange = async (val) => {
    const newVal = Math.max(10, Math.min(200, tankCapacity + val));
    setTankCapacity(newVal);
    await AsyncStorage.setItem('tankCapacity', newVal.toString());
  };

  const handleConsChange = async (val) => {
    const newVal = parseFloat(Math.max(1.0, Math.min(30.0, fuelConsumption + val)).toFixed(1));
    setFuelConsumption(newVal);
    await AsyncStorage.setItem('fuelConsumption', newVal.toString());
  };

  const handleGarageFuelChange = async (type) => {
    smoothTransition();
    setSelectedFuel(type);
    await AsyncStorage.setItem('defaultFuel', type);
  };

  const handleMapFuelChange = (type) => {
    smoothTransition();
    setSelectedFuel(type);
  };

  const selectMake = async (make) => {
    smoothTransition();
    setSelectedMake(make);
    setSelectedModel(null);
    setPickerMode(null);
    await AsyncStorage.setItem('selectedMake', make);
    await AsyncStorage.removeItem('selectedModel');
  };

  const selectModel = async (modelName) => {
    smoothTransition();
    setSelectedModel(modelName);
    setPickerMode(null);
    await AsyncStorage.setItem('selectedModel', modelName);

    if (selectedMake && carDatabase[selectedMake][modelName]) {
      const carData = carDatabase[selectedMake][modelName];
      setTankCapacity(carData.tank);
      setFuelConsumption(carData.cons);
      setSelectedFuel(carData.fuel);
      
      await AsyncStorage.setItem('tankCapacity', carData.tank.toString());
      await AsyncStorage.setItem('fuelConsumption', carData.cons.toString());
      await AsyncStorage.setItem('defaultFuel', carData.fuel);
    }
  };

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
      try {
        const storedTank = await AsyncStorage.getItem('tankCapacity');
        const storedCons = await AsyncStorage.getItem('fuelConsumption');
        const storedFuel = await AsyncStorage.getItem('defaultFuel');
        const storedMake = await AsyncStorage.getItem('selectedMake');
        const storedModel = await AsyncStorage.getItem('selectedModel');

        if (storedTank) setTankCapacity(parseFloat(storedTank));
        if (storedCons) setFuelConsumption(parseFloat(storedCons));
        if (storedFuel) setSelectedFuel(storedFuel);
        if (storedMake) setSelectedMake(storedMake);
        if (storedModel) setSelectedModel(storedModel);
      } catch (err) {
        console.error('Garage load error:', err);
      }

      const { status: locStatus } = await Location.getForegroundPermissionsAsync();
      let locationGranted = locStatus === 'granted';

      if (locStatus !== 'granted') {
        const willAskLoc = await new Promise((resolve) => {
          Alert.alert(
            "Konum İzni Gerekli",
            "Bulunduğunuz konuma göre en kârlı 'Mantıklı' istasyonları bulabilmemiz ve yol masrafınızı hesaplayabilmemiz için konum iznine ihtiyacımız var.",
            [
              { text: "Şimdi Değil", onPress: () => resolve(false), style: "cancel" },
              { text: "İzin Ver", onPress: () => resolve(true) }
            ]
          );
        });

        if (willAskLoc) {
          const { status } = await Location.requestForegroundPermissionsAsync();
          locationGranted = status === 'granted';
        }
      }

      let currentLat = 41.0082; // Varsayılan İstanbul Merkez
      let currentLng = 28.9784;

      if (!locationGranted) {
        setLocation({ latitude: currentLat, longitude: currentLng, latitudeDelta: 0.1, longitudeDelta: 0.1 });
      } else {
        try {
          let loc = await Location.getCurrentPositionAsync({});
          currentLat = loc.coords.latitude;
          currentLng = loc.coords.longitude;
          setLocation({
            latitude: currentLat,
            longitude: currentLng,
            latitudeDelta: 0.05,
            longitudeDelta: 0.05,
          });
        } catch (locErr) {
          Alert.alert("Lokasyon Hatası", "Lütfen internet bağlantınızı ve cihazınızın konum servislerini (GPS) kontrol edin.");
          setLocation({ latitude: currentLat, longitude: currentLng, latitudeDelta: 0.1, longitudeDelta: 0.1 });
        }
      }

      // FOMO Push Bildirim Kurulumu (Cihazı ZAM alarmlarına karsi kaydet)
      if (Device.isDevice) {
        try {
          const token = await registerForPushNotificationsAsync();
          if (token) {
            // Eger tabloya bu token daha once kaydedilmediyse, ekle.
            const { data } = await supabase.from('push_tokens').select('id').eq('token', token);
            if (!data || data.length === 0) {
              await supabase.from('push_tokens').insert({ token });
            }
          }
        } catch (error) {
          console.warn('Push notification initialization failed:', error);
        }
      } else {
        console.log('Must use physical device for Push Notifications');
      }

      fetchStations(currentLat, currentLng);
      fetchNews();
    })();

    // Notification listeners
    notificationListener.current = Notifications.addNotificationReceivedListener(notification => {
      // Foreground notification ops if needed
    });

    responseListener.current = Notifications.addNotificationResponseReceivedListener(response => {
      const data = response.notification.request.content.data;
      if (data && data.url) {
        WebBrowser.openBrowserAsync(data.url).catch(err => console.error("URL failed to open:", err));
      }
    });

    return () => {
      if (notificationListener.current) Notifications.removeNotificationSubscription(notificationListener.current);
      if (responseListener.current) Notifications.removeNotificationSubscription(responseListener.current);
    };
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

  const fetchStations = async (lat, lng) => {
    try {
      // Eğer doğrudan lat/lng gönderilmişse onu kullan, yoksa state'tekini al
      const targetLat = lat || location?.latitude;
      const targetLng = lng || location?.longitude;

      if (!targetLat || !targetLng) return;

      // PostGIS Stored Procedure'ünü (get_nearby_stations) parametrelerle çağırıyoruz.
      // Artık tüm veritabanını DEĞİL, sadece bu koordinatlara 20 km uzaklıktaki max 50 istasyonu çekiyoruz! Mükemmel Performans.
      const { data, error } = await supabase
        .rpc('get_nearby_stations', {
          lat: targetLat,
          lng: targetLng,
          max_dist_meters: 20000 // 20 KM Çap
        })
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
        `);

      if (error) {
        console.error('Supabase Error:', error);
        Alert.alert("Bağlantı Hatası", "Lütfen internet bağlantınızı kontrol edip tekrar deneyin.");
      } else {
        setStations(data || []);
      }
    } catch (err) {
      console.error('Fetch Error:', err);
      Alert.alert("Bağlantı Hatası", "Lütfen internet bağlantınızı kontrol edip tekrar deneyin.");
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
          const costToFill = tankCapacity * price;
          const travelCost = distance * (fuelConsumption / 100) * price;
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

    const myTotalCost = (tankCapacity * price) + (myDistance * (fuelConsumption / 100) * price);

    if (station.id === mostLogicalStationId) {
      if (cheapestStationId && cheapestStationId !== mostLogicalStationId) {
        const cheapSt = stations.find(s => s.id === cheapestStationId);
        if (cheapSt) {
          const cheapPrice = parseFloat(getPrice(cheapSt.fiyatlar, selectedFuel));
          const cheapDist = getDistanceKm(location.latitude, location.longitude, cheapSt.enlem, cheapSt.boylam);
          const cheapTotal = (tankCapacity * cheapPrice) + (cheapDist * (fuelConsumption / 100) * cheapPrice);
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

  const renderedMarkers = useMemo(() => stations.map((station) => {
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
        tracksViewChanges={false}
        onPress={(e) => {
          e.stopPropagation();
          openSheet(station);
        }}
      >
        <View style={[styles.customPin, { backgroundColor: bgColor, borderColor: hasPrice ? '#ffffff' : '#D1D5DB' }]}>
          <Text style={[styles.pinText, { color: textColor }]} allowFontScaling={false}>
            {hasPrice ? `${priceStr} ₺` : 'Yok'}
          </Text>
        </View>
      </Marker>
    );
  }), [stations, selectedFuel, cheapestStationId, mostLogicalStationId]);

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
      
      <View style={{ position: 'absolute', top: Platform.OS === 'ios' ? 60 : 40, width: '100%', alignItems: 'center', zIndex: 99, gap: 15 }}>
        {/* Sondakika Marquee (Kayan Yazi) */}
        <MarqueeBanner news={news} />

        {/* Yakit Tipi Secici */}
        <View style={styles.fuelSelector}>
          {['Kursunsuz 95', 'Motorin', 'LPG'].map(fuel => (
            <TouchableOpacity 
              key={fuel}
              style={[styles.fuelButton, selectedFuel === fuel && styles.fuelButtonActive]}
              onPress={() => handleMapFuelChange(fuel)}
            >
              <Text style={[styles.fuelButtonText, selectedFuel === fuel && styles.fuelButtonTextActive]}>
                {fuel === 'Kursunsuz 95' ? 'Benzin' : fuel}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Garajim FAB */}
        <TouchableOpacity style={styles.garageFab} onPress={() => setGarageVisible(true)} activeOpacity={0.8}>
          <Text style={styles.garageFabIcon}>🚗</Text>
        </TouchableOpacity>
      </View>

      <MapView 
        style={styles.map} 
        initialRegion={location}
        showsUserLocation={true}
        showsMyLocationButton={true}
        onPress={() => closeSheet()}
        onRegionChangeComplete={(region) => {
          // Kullanıcı haritayı kaydırdığında (sürükleme durunca) o bölgenin merkezine göre 20KM 
          // alanındaki yeni istasyonları arka planda sessizce ("loading" döndürmeden) getir.
          fetchStations(region.latitude, region.longitude);
        }}
        clusterColor="#FF5A5F" // Kırmızı fullet rengi
        clusterTextColor="#FFFFFF"
        radius={50} // Pinler bu mesafeye (piksel) girince kümelenir
        animationEnabled={true} // Yakınlaştıkça açılsın/gruplaşsın animasyonu
        spiderLineColor="#FF5A5F"
      >
        {renderedMarkers}
      </MapView>

      {/* Empty State Overlay */}
      {(!loading && stations.length === 0) && (
        <View style={styles.emptyStateContainer} pointerEvents="none">
          <View style={styles.emptyStateBox}>
            <Text style={styles.emptyStateText}>Şu an yakınınızda veri bulunamadı.</Text>
          </View>
        </View>
      )}

      {/* Garajim Modal */}
      <Modal visible={garageVisible} animationType="slide" transparent={true} onRequestClose={() => setGarageVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.garageSheet}>
            <View style={styles.garageHeader}>
              <Text style={styles.garageTitle}>🚗 Garajım</Text>
              <TouchableOpacity onPress={() => { setPickerMode(null); setGarageVisible(false); }} style={styles.closeBtn}>
                <Text style={styles.closeBtnText}>✕</Text>
              </TouchableOpacity>
            </View>
            
            <Text style={styles.garageSubtitle}>Aracınızı seçin, gerisini asistanınıza bırakın.</Text>
            
            {pickerMode === 'make' ? (
              <View style={{ height: 380 }}>
                <TouchableOpacity onPress={() => { smoothTransition(); setPickerMode(null); }} style={styles.pickerBackBtn}>
                  <Text style={styles.pickerBackText}>← Vazgeç</Text>
                </TouchableOpacity>
                <ScrollView showsVerticalScrollIndicator={false}>
                  {Object.keys(carDatabase).map(make => (
                    <TouchableOpacity key={make} style={styles.pickerItem} onPress={() => selectMake(make)}>
                      <Text style={styles.pickerItemText}>{make}</Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>
              </View>
            ) : pickerMode === 'model' ? (
              <View style={{ height: 380 }}>
                <TouchableOpacity onPress={() => { smoothTransition(); setPickerMode(null); }} style={styles.pickerBackBtn}>
                  <Text style={styles.pickerBackText}>← Vazgeç</Text>
                </TouchableOpacity>
                <ScrollView showsVerticalScrollIndicator={false}>
                  {selectedMake && Object.keys(carDatabase[selectedMake]).map(model => (
                    <TouchableOpacity key={model} style={styles.pickerItem} onPress={() => selectModel(model)}>
                      <Text style={styles.pickerItemText}>{model}</Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>
              </View>
            ) : (
              <>
                <View style={styles.carPickerContainer}>
                  <TouchableOpacity style={styles.carPickerBox} onPress={() => { smoothTransition(); setPickerMode('make'); }}>
                    <Text style={styles.carPickerLabel}>MARKANIZ</Text>
                    <Text style={styles.carPickerValue}>{selectedMake || 'Seçin'}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[styles.carPickerBox, !selectedMake && {opacity: 0.5}]} disabled={!selectedMake} onPress={() => { smoothTransition(); setPickerMode('model'); }}>
                    <Text style={styles.carPickerLabel}>MODELİNİZ</Text>
                    <Text style={styles.carPickerValue}>{selectedModel || 'Seçin'}</Text>
                  </TouchableOpacity>
                </View>

                <View style={styles.garageSettingsBlock}>
                  <View style={styles.settingRow}>
                    <Text style={styles.settingLabel}>Depo Hacmi (L)</Text>
                    <View style={styles.stepperControl}>
                      <TouchableOpacity style={styles.stepperBtn} onPress={() => handleTankChange(-1)}>
                        <Text style={styles.stepperBtnText}>-</Text>
                      </TouchableOpacity>
                      <Text style={styles.stepperValue}>{tankCapacity}</Text>
                      <TouchableOpacity style={styles.stepperBtn} onPress={() => handleTankChange(1)}>
                        <Text style={styles.stepperBtnText}>+</Text>
                      </TouchableOpacity>
                    </View>
                  </View>

                  <View style={styles.settingRow}>
                    <Text style={styles.settingLabel}>Şehir İçi (L/100km)</Text>
                    <View style={styles.stepperControl}>
                      <TouchableOpacity style={styles.stepperBtn} onPress={() => handleConsChange(-0.1)}>
                        <Text style={styles.stepperBtnText}>-</Text>
                      </TouchableOpacity>
                      <Text style={styles.stepperValue}>{fuelConsumption.toFixed(1)}</Text>
                      <TouchableOpacity style={styles.stepperBtn} onPress={() => handleConsChange(0.1)}>
                        <Text style={styles.stepperBtnText}>+</Text>
                      </TouchableOpacity>
                    </View>
                  </View>

                  <View style={styles.settingRowCol}>
                    <Text style={styles.settingLabelCentered}>Yakıt Tipi</Text>
                    <View style={styles.garageFuelSelector}>
                      <Animated.View style={{
                        position: 'absolute',
                        top: 4, bottom: 4,
                        width: '32%',
                        left: garageFuelAnim.interpolate({
                          inputRange: [0, 1, 2],
                          outputRange: ['1.5%', '34%', '66.5%']
                        }),
                        backgroundColor: '#10b981',
                        borderRadius: 10,
                      }} />
                      {['Kursunsuz 95', 'Motorin', 'LPG'].map(fuel => (
                        <TouchableOpacity 
                          key={`g-${fuel}`}
                          style={styles.garageFuelBtn}
                          onPress={() => handleGarageFuelChange(fuel)}
                        >
                          <Text style={[styles.garageFuelBtnText, selectedFuel === fuel && styles.garageFuelBtnTextActive]}>
                            {fuel === 'Kursunsuz 95' ? 'Benzin' : fuel}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                </View>
                
                <TouchableOpacity style={styles.saveGarageBtn} onPress={() => setGarageVisible(false)}>
                  <Text style={styles.saveGarageBtnText}>Güncelle ve Kapat</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        </View>
      </Modal>

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
                  <View style={{flexDirection: 'row', alignItems: 'center', marginTop: 4}}>
                    <Text style={{fontSize: 10, color: '#6B7280', fontWeight: 'bold', marginRight: 10}}>🕒 {getLastPriceChangeText(visibleStation)}</Text>
                    {location && visibleStation.enlem && visibleStation.boylam && (
                      <Text style={styles.distanceText}>
                        🚘 {(getDistanceKm(location.latitude, location.longitude, visibleStation.enlem, visibleStation.boylam)).toFixed(1)} KM Uzaklıkta
                      </Text>
                    )}
                  </View>
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

export default Sentry.wrap(App);

const styles = StyleSheet.create({
  emptyStateContainer: {
    position: 'absolute',
    top: '35%',
    width: '100%',
    alignItems: 'center',
    zIndex: 90,
  },
  emptyStateBox: {
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 20,
  },
  emptyStateText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
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
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 25,
    padding: 4,
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
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: '#ffffff',
    elevation: 5,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 3,
    width: 90,
    height: 35,
    overflow: 'hidden',
  },
  pinText: {
    width: 90,
    height: 35,
    lineHeight: 35,
    textAlign: 'center',
    fontSize: 12,
    fontWeight: 'bold',
    color: 'white',
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
  garageFab: {
    backgroundColor: '#111827',
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#10b981',
    shadowOpacity: 0.6,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
    borderWidth: 1.5,
    borderColor: '#10b981',
  },
  garageFabIcon: {
    fontSize: 20,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
    justifyContent: 'flex-end',
  },
  garageSheet: {
    backgroundColor: '#111827',
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    padding: 24,
    paddingBottom: Platform.OS === 'ios' ? 40 : 24,
    elevation: 20,
    borderWidth: 1,
    borderColor: '#1f2937',
  },
  garageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  garageTitle: {
    fontSize: 24,
    fontWeight: '900',
    color: '#10b981',
    letterSpacing: 0.5,
  },
  garageSubtitle: {
    fontSize: 13,
    color: '#9ca3af',
    marginBottom: 20,
    lineHeight: 18,
  },
  garageSettingsBlock: {
    backgroundColor: '#1f2937',
    borderRadius: 24,
    padding: 16,
    marginBottom: 24,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#374151',
  },
  settingRowCol: {
    paddingVertical: 16,
  },
  settingLabel: {
    fontSize: 15,
    color: '#e5e7eb',
    fontWeight: '700',
  },
  settingLabelCentered: {
    fontSize: 14,
    color: '#9ca3af',
    fontWeight: '700',
    marginBottom: 12,
    textAlign: 'center',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  stepperControl: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#374151',
    borderRadius: 14,
    overflow: 'hidden',
  },
  stepperBtn: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#4b5563',
  },
  stepperBtnText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  stepperValue: {
    width: 65,
    textAlign: 'center',
    fontSize: 17,
    fontWeight: '900',
    color: '#10b981',
  },
  garageFuelSelector: {
    flexDirection: 'row',
    backgroundColor: '#374151',
    borderRadius: 14,
    padding: 4,
  },
  garageFuelBtn: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 10,
  },
  garageFuelBtnActive: {
    backgroundColor: '#10b981',
  },
  garageFuelBtnText: {
    fontWeight: '800',
    fontSize: 13,
    color: '#9ca3af',
  },
  garageFuelBtnTextActive: {
    color: '#111827',
  },
  saveGarageBtn: {
    backgroundColor: '#10b981',
    paddingVertical: 18,
    borderRadius: 20,
    alignItems: 'center',
    shadowColor: '#10b981',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 8,
  },
  saveGarageBtnText: {
    color: '#111827',
    fontWeight: '900',
    fontSize: 17,
    letterSpacing: 0.5,
  },
  carPickerContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
    gap: 12,
  },
  carPickerBox: {
    flex: 1,
    backgroundColor: '#1f2937',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#374151',
  },
  carPickerLabel: {
    fontSize: 12,
    color: '#9ca3af',
    fontWeight: '700',
    marginBottom: 8,
    letterSpacing: 0.5,
  },
  carPickerValue: {
    fontSize: 16,
    color: '#10b981',
    fontWeight: '900',
  },
  pickerBackBtn: {
    paddingVertical: 12,
    marginBottom: 10,
  },
  pickerBackText: {
    color: '#10b981',
    fontSize: 16,
    fontWeight: 'bold',
  },
  pickerItem: {
    backgroundColor: '#1f2937',
    padding: 16,
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#374151',
  },
  pickerItemText: {
    color: '#e5e7eb',
    fontSize: 16,
    fontWeight: '600',
  }
});


