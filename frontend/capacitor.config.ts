import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.cerebrum.app',
  appName: 'Cerebrum',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    iosScheme: 'https',
    cleartext: true,
    hostname: 'app.cerebrum.local',
  },
  loggingBehavior: 'production',
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: '#000000',
      androidSplashResourceName: 'splash',
      androidScaleType: 'CENTER_CROP',
      showSpinner: true,
      androidSpinnerStyle: 'large',
      iosSpinnerStyle: 'small',
      spinnerColor: '#999999',
    },
    LocalNotifications: {
      smallIcon: 'ic_stat_icon_config_sample',
      iconColor: '#000000',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    Camera: {
      allowEditing: false,
      saveToGallery: false,
      resultType: 'uri',
    },
    CapacitorSQLite: {
      iosDatabaseLocation: 'Library/CerebrumDatabase',
      iosIsEncryption: false,
      iosKeychainPrefix: 'cerebrum',
      iosBiometric: {
        biometricAuth: false,
        biometricTitle: 'Authentication',
      },
      androidIsEncryption: false,
      androidBiometric: {
        biometricAuth: false,
        biometricTitle: 'Authentication',
        biometricSubTitle: 'Log in using your biometric',
      },
      electronIsEncryption: false,
      electronWindowsLocation: 'CerebrumDatabase',
      electronMacLocation: '/Users/YOUR_NAME/CerebrumDatabase',
      electronLinuxLocation: '/var/CerebrumDatabase',
    },
  },
  android: {
    buildOptions: {
      keystorePath: undefined,
      keystoreAlias: undefined,
    },
    allowMixedContent: true,
    captureInput: true,
  },
  ios: {
    contentInset: 'automatic',
    scrollEnabled: true,
  },
};

export default config;