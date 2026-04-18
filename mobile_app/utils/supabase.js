import 'react-native-url-polyfill/auto';
import { createClient } from '@supabase/supabase-js';

// EXPO_PUBLIC_ prefix'li degiskenleri Expo otomatik olarak algilar
const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
