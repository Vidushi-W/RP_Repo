import React, { useState } from 'react';
import { SafeAreaView, StatusBar, StyleSheet } from 'react-native';
import { AppProvider } from './src/state/AppContext';
import { colors } from './src/theme';
import { BottomNavigation } from './src/components/BottomNavigation';
import { HomeScreen } from './src/screens/HomeScreen';
import { AlertsScreen } from './src/screens/AlertsScreen';
import { GuideScreen } from './src/screens/GuideScreen';
import { SettingsScreen } from './src/screens/SettingsScreen';

function AppShell() {
  const [route, setRoute] = useState('home');

  return (
    <SafeAreaView style={styles.app}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.cream} />
      {route === 'home' && <HomeScreen navigate={setRoute} />}
      {route === 'alerts' && <AlertsScreen navigate={setRoute} />}
      {route === 'guide' && <GuideScreen navigate={setRoute} />}
      {route === 'settings' && <SettingsScreen navigate={setRoute} />}
      <BottomNavigation active={route} onNavigate={setRoute} />
    </SafeAreaView>
  );
}

export default function App() {
  return <AppProvider><AppShell /></AppProvider>;
}

const styles = StyleSheet.create({ app: { flex: 1, backgroundColor: colors.cream } });
