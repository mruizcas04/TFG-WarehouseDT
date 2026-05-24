import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import EyeIcon from '../components/EyeIcon';
import { API_URL, apiFetch } from '../api/client';
import { COLORS, TYPOGRAPHY, SPACING, RADIUS } from '../theme';

export default function LoginScreen({ navigation }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Introduce email y contraseña');
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        Alert.alert('Error', 'Credenciales incorrectas');
        return;
      }

      const data = await res.json();
      const base64Url = data.access_token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(decodeURIComponent(
        atob(base64).split('').map(c => '%' + c.charCodeAt(0).toString(16).padStart(2, '0')).join('')
      ));

      const me = await apiFetch('/auth/me', {}, data.access_token);

      login({
        token: data.access_token,
        id: payload.sub,
        role: payload.role,
        name: me.name,
        email: me.email,
        created_at: me.created_at,
        must_change_password: payload.must_change_password ?? false,
      });
    } catch (e) {
      Alert.alert('Error de conexión', e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.card}>
        <View style={styles.logoContainer}>
          <View style={styles.logoIcon}>
            <Text style={styles.logoIconText}>W</Text>
          </View>
          <Text style={styles.title}>Warehouse</Text>
          <Text style={styles.subtitle}>ACCESO OPERARIOS</Text>
        </View>

        <Text style={styles.label}>EMAIL</Text>
        <TextInput
          style={styles.input}
          placeholder="correo@ejemplo.com"
          placeholderTextColor={COLORS.textSecondary}
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />

        <Text style={styles.label}>CONTRASEÑA</Text>
        <View style={styles.inputWrapper}>
          <TextInput
            style={[styles.input, styles.inputWithEye]}
            placeholder="••••••••"
            placeholderTextColor={COLORS.textSecondary}
            secureTextEntry={!showPassword}
            value={password}
            onChangeText={setPassword}
          />
          <TouchableOpacity style={styles.eyeButton} onPress={() => setShowPassword(v => !v)}>
            <EyeIcon visible={showPassword} color={COLORS.textSecondary} />
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.buttonText}>Entrar</Text>
          }
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.forgotLink}
          onPress={() => navigation.navigate('ForgotPassword')}
        >
          <Text style={styles.forgotLinkText}>¿Olvidaste tu contraseña?</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.surfaceAlt,
    justifyContent: 'center',
    alignItems: 'center',
  },
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    padding: SPACING.xxl,
    width: '88%',
    borderWidth: 0.5,
    borderColor: COLORS.borderInput,
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: SPACING.xxl,
  },
  logoIcon: {
    width: 44,
    height: 44,
    borderRadius: RADIUS.md,
    backgroundColor: COLORS.accent,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.sm,
  },
  logoIconText: {
    color: '#fff',
    fontSize: TYPOGRAPHY.large,
    fontWeight: '700',
  },
  title: {
    fontSize: TYPOGRAPHY.large,
    fontWeight: '500',
    color: COLORS.textPrimary,
    marginBottom: 2,
  },
  subtitle: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
    letterSpacing: 0.06,
  },
  label: {
    fontSize: TYPOGRAPHY.tiny,
    fontWeight: '500',
    color: COLORS.textSecondary,
    letterSpacing: 0.04,
    marginBottom: SPACING.xs,
    marginTop: SPACING.sm,
  },
  inputWrapper: {
    position: 'relative',
  },
  input: {
    backgroundColor: COLORS.surface,
    color: COLORS.textPrimary,
    borderRadius: RADIUS.md,
    borderWidth: 0.5,
    borderColor: COLORS.borderInput,
    padding: SPACING.md,
    fontSize: TYPOGRAPHY.body,
  },
  inputWithEye: {
    paddingRight: 44,
  },
  eyeButton: {
    position: 'absolute',
    right: SPACING.md,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
  },
  button: {
    backgroundColor: COLORS.accent,
    borderRadius: RADIUS.md,
    padding: 14,
    alignItems: 'center',
    marginTop: SPACING.lg,
  },
  buttonDisabled: {
    backgroundColor: '#B5D4F4',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '500',
    fontSize: TYPOGRAPHY.body,
  },
  forgotLink: {
    alignItems: 'center',
    marginTop: SPACING.md,
    padding: SPACING.sm,
  },
  forgotLinkText: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
  },
});
