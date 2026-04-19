import React, { useRef, useMemo, useEffect } from 'react';
import { StyleSheet, View, Text, TouchableOpacity, Animated, Easing } from 'react-native';
import * as WebBrowser from 'expo-web-browser';

const MarqueeBanner = ({ news }) => {
  const animatedValue = useRef(new Animated.Value(0)).current;

  // Gelen kisa haber listesini kopyalayip arda arda yikiyoruz.
  const displayNews = useMemo(() => {
    if (!news || news.length === 0) return [];
    let padded = [...news];
    for (let i = 0; i < 20; i++) {
        padded = [...padded, ...news];
    }
    return padded;
  }, [news]);

  // Tum kopyalarin kaplayacagi devasa genisligi hesapliyoruz
  const fullTextLength = displayNews.reduce((acc, curr) => acc + (curr.baslik || '').length + (curr.kaynak || '').length + 15, 0);
  const containerWidth = fullTextLength * 8.5; 

  useEffect(() => {
    if (displayNews.length === 0) return;
    
    animatedValue.setValue(0);
    const duration = (containerWidth / 45) * 1000; 

    const animation = Animated.loop(
      Animated.timing(animatedValue, {
        toValue: -containerWidth, 
        duration: duration,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    );
    
    animation.start();

    return () => animation.stop();
  }, [displayNews, containerWidth]);

  if (!news || news.length === 0) return null;

  return (
    <View style={styles.marqueeContainer}>
      <View style={styles.marqueeLabelBox}>
        <Text style={styles.marqueeLabelText}>SONDAKİKA</Text>
      </View>
      <View style={styles.marqueeTrack}>
        {/* En kritik çözüm: Yazilarin sigmayip kesilmemesi (truncate olmamasi) icin 
            taşıyıcı View'e eksiksiz hesaplanmis Devasa bir Genislik (width) veriyoruz! */}
        <Animated.View style={{ width: containerWidth, flexDirection: 'row', transform: [{ translateX: animatedValue }] }}>
          {displayNews.map((n, i) => (
            <TouchableOpacity 
              key={i} 
              activeOpacity={0.6}
              onPress={() => WebBrowser.openBrowserAsync(n.link).catch(err => console.error("Link acilamadi:", err))}
            >
              <Text style={styles.marqueeText} numberOfLines={1}>🔴 {n.baslik} [{n.kaynak}]   |   </Text>
            </TouchableOpacity>
          ))}
        </Animated.View>
      </View>
    </View>
  );
};

export default MarqueeBanner;

const styles = StyleSheet.create({
  marqueeContainer: {
    width: '92%',
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
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
  },
});
