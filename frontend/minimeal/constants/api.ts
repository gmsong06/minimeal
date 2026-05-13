import { Platform } from 'react-native';

function getDefaultApiBaseUrl() {
  const configuredBaseUrl = process.env.EXPO_PUBLIC_MINIMEAL_API_BASE_URL?.trim();
  if (configuredBaseUrl) {
    return configuredBaseUrl.replace(/\/+$/, '');
  }

  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }

  return 'http://127.0.0.1:8000';
}

export const API_BASE_URL = getDefaultApiBaseUrl();
