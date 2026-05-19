import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../context/AuthContext';
import LoginScreen from '../screens/LoginScreen';
import TasksScreen from '../screens/TasksScreen';
import MoveScreen from '../screens/MoveScreen';
import SetupNFCScreen from '../screens/SetupNFCScreen';
import ChangePasswordScreen from '../screens/ChangePasswordScreen';

const Stack = createNativeStackNavigator();

export default function RootNavigator() {
  const { user } = useAuth();

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!user ? (
        <Stack.Screen name="Login" component={LoginScreen} />
      ) : user.must_change_password ? (
        <Stack.Screen
          name="ChangePassword"
          component={ChangePasswordScreen}
          options={{ gestureEnabled: false }}
        />
      ) : (
        <>
          <Stack.Screen name="Tasks" component={TasksScreen} />
          <Stack.Screen name="Move" component={MoveScreen} />
          <Stack.Screen name="SetupNFC" component={SetupNFCScreen} />
        </>
      )}
    </Stack.Navigator>
  );
}
