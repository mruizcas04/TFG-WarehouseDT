import React from 'react';
import { View, StyleSheet } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { getFocusedRouteNameFromRoute } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../theme';

import LoginScreen          from '../screens/LoginScreen';
import ForgotPasswordScreen from '../screens/ForgotPasswordScreen';
import ChangePasswordScreen from '../screens/ChangePasswordScreen';
import TasksScreen          from '../screens/TasksScreen';
import TaskDetailScreen     from '../screens/TaskDetailScreen';
import MoveScreen           from '../screens/MoveScreen';
import SetupNFCScreen       from '../screens/SetupNFCScreen';
import HistoryScreen        from '../screens/HistoryScreen';
import ProfileScreen        from '../screens/ProfileScreen';

const Stack = createNativeStackNavigator();
const Tab   = createBottomTabNavigator();

// --- Iconos dibujados con View (sin dependencias nativas) ---

function IconTasks({ color }) {
  return (
    <View style={styles.icon}>
      {[0, 1, 2].map(i => (
        <View key={i} style={[styles.listLine, { backgroundColor: color }, i === 0 && styles.listLineShort]} />
      ))}
    </View>
  );
}

function IconHistory({ color }) {
  return (
    <View style={styles.icon}>
      <View style={[styles.clockCircle, { borderColor: color }]}>
        {/* Minute hand: center → 12 o'clock */}
        <View style={{
          position: 'absolute',
          width: 1.5, height: 5,
          backgroundColor: color,
          borderRadius: 1,
          bottom: '50%',
          left: '50%',
          marginLeft: -0.75,
        }} />
        {/* Hour hand: center → 3 o'clock */}
        <View style={{
          position: 'absolute',
          height: 1.5, width: 5,
          backgroundColor: color,
          borderRadius: 1,
          top: '50%',
          left: '50%',
          marginTop: -0.75,
        }} />
      </View>
    </View>
  );
}

function IconProfile({ color }) {
  return (
    <View style={styles.icon}>
      <View style={[styles.profileHead, { borderColor: color }]} />
      <View style={[styles.profileBody, { borderColor: color }]} />
    </View>
  );
}

// --- Navegación ---

function TasksStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Tasks"      component={TasksScreen} />
      <Stack.Screen name="TaskDetail" component={TaskDetailScreen} />
      <Stack.Screen name="Move"       component={MoveScreen} />
      <Stack.Screen name="SetupNFC"   component={SetupNFCScreen} />
    </Stack.Navigator>
  );
}

function getTabBarStyle(route) {
  const focused = getFocusedRouteNameFromRoute(route);
  if (focused === 'TaskDetail' || focused === 'Move' || focused === 'SetupNFC') {
    return { display: 'none' };
  }
  return {
    backgroundColor: COLORS.surface,
    borderTopColor: COLORS.border,
    borderTopWidth: 0.5,
  };
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: COLORS.accent,
        tabBarInactiveTintColor: COLORS.textSecondary,
        tabBarStyle: {
          backgroundColor: COLORS.surface,
          borderTopColor: COLORS.border,
          borderTopWidth: 0.5,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
          marginBottom: 2,
        },
      }}
    >
      <Tab.Screen
        name="TasksTab"
        component={TasksStack}
        options={({ route }) => ({
          title: 'Tareas',
          tabBarStyle: getTabBarStyle(route),
          tabBarIcon: ({ color }) => <IconTasks color={color} />,
        })}
      />
      <Tab.Screen
        name="History"
        component={HistoryScreen}
        options={{
          title: 'Historial',
          tabBarIcon: ({ color }) => <IconHistory color={color} />,
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: 'Perfil',
          tabBarIcon: ({ color }) => <IconProfile color={color} />,
        }}
      />
    </Tab.Navigator>
  );
}

export default function RootNavigator() {
  const { user } = useAuth();

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!user ? (
        <>
          <Stack.Screen name="Login"          component={LoginScreen} />
          <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
        </>
      ) : user.must_change_password ? (
        <Stack.Screen
          name="ChangePassword"
          component={ChangePasswordScreen}
          options={{ gestureEnabled: false }}
        />
      ) : (
        <Stack.Screen name="Main" component={MainTabs} />
      )}
    </Stack.Navigator>
  );
}

const styles = StyleSheet.create({
  icon: {
    width: 22,
    height: 22,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 3.5,
  },
  // Lista (Tareas)
  listLine: {
    width: 16,
    height: 2,
    borderRadius: 1,
    alignSelf: 'flex-start',
  },
  listLineShort: {
    width: 11,
  },
  // Reloj (Historial)
  clockCircle: {
    width: 17,
    height: 17,
    borderRadius: 9,
    borderWidth: 1.8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  // Persona (Perfil)
  profileHead: {
    width: 9,
    height: 9,
    borderRadius: 5,
    borderWidth: 1.8,
  },
  profileBody: {
    width: 15,
    height: 7,
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
    borderWidth: 1.8,
    borderBottomWidth: 0,
    marginTop: 1,
  },
});
