import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  StatusBar, Alert, ScrollView, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/client';
import {
  COLORS, TYPOGRAPHY, SPACING, RADIUS, SHADOW,
} from '../theme';

const ROLE_LABELS = {
  admin:  'Administrador',
  worker: 'Operario',
};

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('es-ES', {
    day: '2-digit', month: 'long', year: 'numeric',
  });
}

function getInitials(name = '') {
  return name
    .split(' ')
    .slice(0, 2)
    .map(w => w[0]?.toUpperCase() ?? '')
    .join('');
}

function InfoRow({ label, value }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const navigation = useNavigation();
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    apiFetch('/auth/me', {}, user.token)
      .then(setProfile)
      .catch(() => {}); // fallback to user object if fetch fails
  }, [user.token]);

  const data = profile ?? user;

  const handleLogout = () => {
    Alert.alert(
      'Cerrar sesión',
      '¿Seguro que quieres salir?',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Salir', style: 'destructive', onPress: logout },
      ]
    );
  };

  const initials  = getInitials(data.name);
  const roleLabel = ROLE_LABELS[data.role] ?? data.role;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.bg} />

      <View style={styles.pageHeader}>
        <Text style={styles.pageTitle}>Perfil</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* Avatar + name block */}
        <View style={styles.avatarSection}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{initials}</Text>
          </View>
          <Text style={styles.userName}>{data.name}</Text>
          <View style={styles.rolePill}>
            <Text style={styles.roleText}>{roleLabel.toUpperCase()}</Text>
          </View>
        </View>

        {/* Info card */}
        <View style={[styles.card, SHADOW.card]}>
          <Text style={styles.cardTitle}>INFORMACIÓN DE CUENTA</Text>
          <InfoRow label="Correo" value={data.email} />
          <View style={styles.divider} />
          <InfoRow label="Rol" value={roleLabel} />
          {data.created_at && (
            <>
              <View style={styles.divider} />
              <InfoRow label="Miembro desde" value={formatDate(data.created_at)} />
            </>
          )}
        </View>

        {/* Admin actions */}
        {data.role === 'admin' && (
          <View style={[styles.card, SHADOW.card]}>
            <Text style={styles.cardTitle}>ADMINISTRACIÓN</Text>
            <TouchableOpacity
              style={styles.actionRow}
              onPress={() => navigation.navigate('TasksTab', { screen: 'SetupNFC' })}
              activeOpacity={0.7}
            >
              <Text style={styles.actionText}>Configurar etiquetas NFC</Text>
              <Text style={styles.actionChevron}>›</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Logout */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout} activeOpacity={0.8}>
          <Text style={styles.logoutText}>Cerrar sesión</Text>
        </TouchableOpacity>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  pageHeader: {
    paddingHorizontal: SPACING.xl,
    paddingTop: SPACING.lg,
    paddingBottom: SPACING.md,
    borderBottomWidth: 0.5,
    borderBottomColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  pageTitle: {
    fontSize: TYPOGRAPHY.title,
    fontWeight: '600',
    color: COLORS.textPrimary,
  },
  scroll: {
    paddingHorizontal: SPACING.xl,
    paddingTop: SPACING.xl,
    paddingBottom: SPACING.xxl * 2,
    gap: SPACING.lg,
  },
  avatarSection: {
    alignItems: 'center',
    paddingVertical: SPACING.lg,
    gap: SPACING.sm,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.accent,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.xs,
  },
  avatarText: {
    color: '#fff',
    fontSize: 28,
    fontWeight: '600',
    letterSpacing: 1,
  },
  userName: {
    fontSize: TYPOGRAPHY.title,
    fontWeight: '600',
    color: COLORS.textPrimary,
  },
  rolePill: {
    backgroundColor: COLORS.accentBg,
    paddingHorizontal: SPACING.md,
    paddingVertical: 4,
    borderRadius: RADIUS.pill,
  },
  roleText: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.accent,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.xl,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    overflow: 'hidden',
  },
  cardTitle: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
    fontWeight: '600',
    letterSpacing: 0.5,
    paddingHorizontal: SPACING.lg,
    paddingTop: SPACING.lg,
    paddingBottom: SPACING.sm,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
  },
  infoLabel: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
  },
  infoValue: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textPrimary,
    fontWeight: '500',
    flexShrink: 1,
    textAlign: 'right',
    marginLeft: SPACING.md,
  },
  divider: {
    height: 0.5,
    backgroundColor: COLORS.border,
    marginHorizontal: SPACING.lg,
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
    marginBottom: SPACING.xs,
  },
  actionText: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textPrimary,
  },
  actionChevron: {
    fontSize: 20,
    color: COLORS.textSecondary,
  },
  logoutButton: {
    backgroundColor: COLORS.errorBg,
    borderRadius: RADIUS.xl,
    borderWidth: 0.5,
    borderColor: '#F5C9C9',
    paddingVertical: SPACING.lg,
    alignItems: 'center',
    marginTop: SPACING.sm,
  },
  logoutText: {
    fontSize: TYPOGRAPHY.body,
    fontWeight: '600',
    color: COLORS.error,
  },
});
