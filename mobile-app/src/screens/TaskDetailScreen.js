import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert, ScrollView, StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/client';
import {
  COLORS, TYPE_COLORS, TYPE_LABELS, STATUS_COLORS, STATUS_LABELS,
  TYPOGRAPHY, SPACING, RADIUS, SHADOW,
} from '../theme';

function formatLocation(loc) {
  if (!loc) return '—';
  const parts = [];
  if (loc.aisle_number != null) parts.push(`Pasillo ${loc.aisle_number}`);
  if (loc.shelf_number != null) parts.push(`Est. ${loc.shelf_number}`);
  if (loc.level_number != null) parts.push(`Balda ${loc.level_number}`);
  parts.push(`Hueco ${loc.position_number}`);
  return parts.join(' · ');
}

export default function TaskDetailScreen() {
  const navigation = useNavigation();
  const route      = useRoute();
  const { user }   = useAuth();
  const { task, originLoc, destLoc, product } = route.params;
  const [starting, setStarting] = useState(false);

  const typeColor   = TYPE_COLORS[task.type]   || TYPE_COLORS.entrada;
  const statusColor = STATUS_COLORS[task.status] || STATUS_COLORS.pendiente;
  const isInProgress = task.status === 'en_curso';

  const handleStart = async () => {
    setStarting(true);
    try {
      if (!isInProgress) {
        await apiFetch(`/tasks/${task.id}/status`, {
          method: 'PUT',
          body: JSON.stringify({ status: 'en_curso' }),
        }, user.token);
      }
      navigation.navigate('Move', {
        task: { ...task, status: 'en_curso' },
        taskOriginLoc: originLoc,
        taskDestLoc:   destLoc,
        taskProduct:   product,
      });
    } catch (e) {
      Alert.alert('Error', e.message || 'No se pudo iniciar la tarea.');
    } finally {
      setStarting(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.surface} />

      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>‹ Volver</Text>
        </TouchableOpacity>
        <View style={[styles.badge, { backgroundColor: typeColor.bg }]}>
          <Text style={[styles.badgeText, { color: typeColor.text }]}>{TYPE_LABELS[task.type]}</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        <View style={styles.titleSection}>
          <View style={styles.titleRow}>
            <Text style={styles.title}>Detalle de tarea</Text>
            <View style={[styles.statusBadge, { backgroundColor: statusColor.bg }]}>
              <Text style={[styles.statusText, { color: statusColor.text }]}>
                {STATUS_LABELS[task.status]}
              </Text>
            </View>
          </View>
          <Text style={styles.taskId}>#{task.id.split('-')[0].toUpperCase()}</Text>
        </View>

        {(task.type === 'salida' || task.type === 'traslado') && (
          <View style={[styles.infoCard, SHADOW.card]}>
            <Text style={styles.infoLabel}>UBICACIÓN ORIGEN</Text>
            <Text style={styles.infoValue}>{formatLocation(originLoc)}</Text>
          </View>
        )}

        {(task.type === 'entrada' || task.type === 'traslado') && (
          <View style={[styles.infoCard, SHADOW.card]}>
            <Text style={styles.infoLabel}>UBICACIÓN DESTINO</Text>
            <Text style={styles.infoValue}>{formatLocation(destLoc)}</Text>
          </View>
        )}

        {product && (
          <View style={[styles.infoCard, SHADOW.card]}>
            <Text style={styles.infoLabel}>PRODUCTO</Text>
            <Text style={styles.infoValue}>{product.name}</Text>
            {product.barcode && (
              <Text style={styles.infoSub}>{product.barcode}</Text>
            )}
          </View>
        )}

        {task.quantity != null && (
          <View style={[styles.infoCard, SHADOW.card]}>
            <Text style={styles.infoLabel}>CANTIDAD</Text>
            <Text style={styles.infoValue}>{task.quantity} unidades</Text>
          </View>
        )}

        <TouchableOpacity
          style={[styles.startButton, starting && styles.startButtonDisabled]}
          onPress={handleStart}
          disabled={starting}
        >
          {starting
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.startButtonText}>
                {isInProgress ? 'Continuar tarea' : 'Comenzar tarea'}
              </Text>
          }
        </TouchableOpacity>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: SPACING.xl,
    paddingVertical: SPACING.md,
    borderBottomWidth: 0.5,
    borderBottomColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  backText:  { fontSize: TYPOGRAPHY.body, color: COLORS.accent, fontWeight: '500' },
  badge:     { paddingHorizontal: SPACING.sm, paddingVertical: 3, borderRadius: RADIUS.pill },
  badgeText: { fontSize: TYPOGRAPHY.tiny, fontWeight: '500' },

  scroll: {
    padding: SPACING.xl,
    gap: SPACING.md,
  },
  titleSection: {
    marginBottom: SPACING.xs,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.xs,
  },
  title: {
    fontSize: TYPOGRAPHY.title,
    fontWeight: '600',
    color: COLORS.textPrimary,
  },
  statusBadge: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: 3,
    borderRadius: RADIUS.pill,
  },
  statusText: {
    fontSize: TYPOGRAPHY.tiny,
    fontWeight: '600',
  },
  taskId: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textTertiary,
    fontFamily: 'monospace',
  },
  infoCard: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    padding: SPACING.lg,
  },
  infoLabel: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
    letterSpacing: 0.04,
    fontWeight: '500',
    marginBottom: SPACING.xs,
  },
  infoValue: {
    fontSize: TYPOGRAPHY.medium,
    color: COLORS.textPrimary,
    fontWeight: '500',
  },
  infoSub: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
    marginTop: 2,
    fontFamily: 'monospace',
  },
  startButton: {
    backgroundColor: COLORS.accent,
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    alignItems: 'center',
    marginTop: SPACING.sm,
  },
  startButtonDisabled: { backgroundColor: '#B5D4F4' },
  startButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: TYPOGRAPHY.medium,
  },
});
