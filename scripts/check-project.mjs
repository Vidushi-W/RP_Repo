import { readFile, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const packageJson = JSON.parse(await readFile(path.join(root, 'package.json'), 'utf8'));
const appJson = JSON.parse(await readFile(path.join(root, 'app.json'), 'utf8'));

if (!appJson.expo?.slug) throw new Error('Expo app slug is missing.');

const sourceFiles = ['App.js', 'src/state/AppContext.js', 'src/components/UI.js', 'src/components/BottomNavigation.js', 'src/screens/HomeScreen.js', 'src/screens/AlertsScreen.js', 'src/screens/GuideScreen.js', 'src/screens/SettingsScreen.js', 'src/theme.js', 'src/sound-analysis/analysis.mjs', 'src/sound-analysis/reasoning.mjs', 'src/haptics/patterns.mjs', 'src/haptics/bleActuatorAdapter.mjs', 'src/history/alertHistory.mjs', 'src/settings/settingsStore.mjs'];
for (const relative of sourceFiles) await access(path.join(root, relative));

const importedFiles = new Set();
for (const relative of sourceFiles) {
  const source = await readFile(path.join(root, relative), 'utf8');
  for (const match of source.matchAll(/from\s+['"](\.[^'"]+)['"]/g)) {
    const base = path.resolve(root, path.dirname(relative), match[1]);
    importedFiles.add(path.extname(base) ? base : `${base}.js`);
  }
  if (source.includes("from '@expo/vector-icons'") && !packageJson.dependencies?.['@expo/vector-icons']) {
    throw new Error(`${relative} imports @expo/vector-icons, but it is not declared.`);
  }
  if (source.includes("from 'expo-document-picker'") && !packageJson.dependencies?.['expo-document-picker']) {
    throw new Error(`${relative} imports expo-document-picker, but it is not declared.`);
  }
  if (source.includes("from 'expo-haptics'") && !packageJson.dependencies?.['expo-haptics']) {
    throw new Error(`${relative} imports expo-haptics, but it is not declared.`);
  }
  if (source.includes("from '@react-native-async-storage/async-storage'") && !packageJson.dependencies?.['@react-native-async-storage/async-storage']) {
    throw new Error(`${relative} imports AsyncStorage, but it is not declared.`);
  }
  if (source.includes("from 'expo-file-system'") && !packageJson.dependencies?.['expo-file-system']) {
    throw new Error(`${relative} imports expo-file-system, but it is not declared.`);
  }
}
for (const file of importedFiles) await access(file);

for (const dependency of ['expo', 'react', 'react-native', '@expo/vector-icons', 'expo-haptics', '@react-native-async-storage/async-storage', 'expo-file-system']) {
  if (!packageJson.dependencies?.[dependency]) throw new Error(`Missing dependency: ${dependency}`);
}

console.log(`Project files and configuration look consistent (${sourceFiles.length} source files checked).`);
