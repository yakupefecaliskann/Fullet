import { Platform, Alert } from 'react-native';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';

export async function registerForPushNotificationsAsync() {
  let token;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF231F7C',
    });
  }

  if (Device.isDevice) {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    
    if (existingStatus !== 'granted') {
      const willAsk = await new Promise((resolve) => {
        Alert.alert(
          "Bildirim İzni",
          "Piyasadaki akaryakıt zam ve indirimlerini anında öğrenerek deponuzu kârlı bir şekilde doldurmak için bildirimlere izin vermeniz gerekmektedir.",
          [
            { text: "Şimdi Değil", onPress: () => resolve(false), style: "cancel" },
            { text: "İzin Ver", onPress: () => resolve(true) }
          ]
        );
      });

      if (willAsk) {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }
    }
    
    if (finalStatus !== 'granted') {
      console.log('Bildirim izni alinmadi!');
      return null;
    }
    
    // EAS Project ID varsa al, yoksa Expo Go kullanimi icin gec
    const projectId = Constants?.expoConfig?.extra?.eas?.projectId ?? Constants?.easConfig?.projectId;
    
    try {
      token = (await Notifications.getExpoPushTokenAsync(
        projectId ? { projectId } : {}
      )).data;
    } catch (e) {
      console.log("Token Alinirken Hata Islendi:", e);
    }
  } else {
    console.log('Push bildirimleri icin fiziksel cihaz kullanilmalidir.');
  }

  return token;
}
