import React, { useState, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert, RefreshControl, StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/client';
import { formatLocation } from '../utils/formatLocation';
import {
  COLORS, STATUS_COLORS, TYPE_COLORS, STATUS_LABELS, TYPE_LABELS,
  TYPOGRAPHY, SPACING, RADIUS, SHADOW,
} from '../theme';

function getGreeting() {
  const h = new Date().getHours();
  if (h < 14) return 'Buenos días';
  if (h < 21) return 'Buenas tardes';
  return 'Buenas noches';
}

function getFirstName(name = '') {
  return name.split(' ')[0];
}

export default function TasksScreen() {
  const { user } = useAuth();
  const navigation = useNavigation();
  const [tasks, setTasks] = useState([]);
  const [locationsMap, setLocationsMap] = useState({});
  const [productsMap, setProductsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await apiFetch(`/tasks/user/${user.id}`, {}, user.token);
      const active = data.filter(t => t.status !== 'completada');
      setTasks(active);

      // Collect unique location and product IDs
      const locationIds = new Set();
      const productIds = new Set();
      active.forEach(t => {
        if (t.origin_location_id) locationIds.add(t.origin_location_id);
        if (t.destination_location_id) locationIds.add(t.destination_location_id);
        if (t.product_id) productIds.add(t.product_id);
      });

      const [locationResults, productResults] = await Promise.all([
        Promise.all([...locationIds].map(id =>
          apiFetch(`/locations/${id}`, {}, user.token).catch(() => null)
        )),
        Promise.all([...productIds].map(id =>
          apiFetch(`/products/${id}`, {}, user.token).catch(() => null)
        )),
      ]);

      const locMap = {};
      [...locationIds].forEach((id, i) => { if (locationResults[i]) locMap[id] = locationResults[i]; });
      setLocationsMap(locMap);

      const prodMap = {};
      [...productIds].forEach((id, i) => { if (productResults[i]) prodMap[id] = productResults[i]; });
      setProductsMap(prodMap);
    } catch {
      Alert.alert('Error', 'No se pudieron cargar las tareas');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user]);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchTasks();
    }, [fetchTasks])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchTasks();
  };

  const handleTaskPress = (task) => {
    const originLoc = task.origin_location_id ? locationsMap[task.origin_location_id] : null;
    const destLoc   = task.destination_location_id ? locationsMap[task.destination_location_id] : null;
    const product   = task.product_id ? productsMap[task.product_id] : null;
    navigation.navigate('TaskDetail', { task, originLoc, destLoc, product });
  };

  const renderTask = ({ item }) => {
    const statusColor = STATUS_COLORS[item.status] || STATUS_COLORS.pendiente;
    const typeColor = TYPE_COLORS[item.type] || TYPE_COLORS.entrada;
    const date = new Date(item.created_at).toLocaleDateString('es-ES', {
      day: '2-digit', month: 'short',
    });

    const originLoc = item.origin_location_id ? locationsMap[item.origin_location_id] : null;
    const destLoc   = item.destination_location_id ? locationsMap[item.destination_location_id] : null;
    const product   = item.product_id ? productsMap[item.product_id] : null;

    let locationLine = null;
    if (item.type === 'entrada' && destLoc) {
      locationLine = formatLocation(destLoc);
    } else if (item.type === 'salida' && originLoc) {
      locationLine = formatLocation(originLoc);
    } else if (item.type === 'traslado') {
      const from = formatLocation(originLoc) ?? '—';
      const to   = formatLocation(destLoc)   ?? '—';
      locationLine = `${from}  →  ${to}`;
    }

    return (
      <TouchableOpacity
        style={[styles.taskCard, SHADOW.card]}
        onPress={() => handleTaskPress(item)}
        activeOpacity={0.75}
      >
        {/* Left accent stripe */}
        <View style={[styles.accentBar, { backgroundColor: typeColor.text }]} />

        <View style={styles.cardBody}>
          {/* Top row: type label + status badge */}
          <View style={styles.topRow}>
            <Text style={[styles.typeLabel, { color: typeColor.text }]}>
              {TYPE_LABELS[item.type]}
            </Text>
            <View style={[styles.statusBadge, { backgroundColor: statusColor.bg }]}>
              <Text style={[styles.statusText, { color: statusColor.text }]}>
                {STATUS_LABELS[item.status]}
              </Text>
            </View>
          </View>

          {/* Location */}
          {locationLine && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>
                {item.type === 'traslado' ? 'Traslado' : item.type === 'entrada' ? 'Destino' : 'Origen'}
              </Text>
              <Text style={styles.detailValue} numberOfLines={2}>{locationLine}</Text>
            </View>
          )}

          {/* Product */}
          {product && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Producto</Text>
              <Text style={styles.detailValue} numberOfLines={1}>
                {product.name}{product.barcode ? ` · ${product.barcode}` : ''}
              </Text>
            </View>
          )}

          {/* Quantity */}
          {item.quantity != null && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Cantidad</Text>
              <Text style={styles.detailValue}>{item.quantity} unidades</Text>
            </View>
          )}

          {/* Footer */}
          <View style={styles.cardFooter}>
            <Text style={styles.taskId}>#{item.id.split('-')[0].toUpperCase()}</Text>
            <Text style={styles.taskDate}>{date}</Text>
            <Text style={styles.arrow}>›</Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  const pending    = tasks.filter(t => t.status === 'pendiente').length;
  const inProgress = tasks.filter(t => t.status === 'en_curso').length;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.surface} />

      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>{getGreeting()},</Text>
          <Text style={styles.userName}>{getFirstName(user.name)}</Text>
        </View>
        <View style={styles.statsRow}>
          {inProgress > 0 && (
            <View style={[styles.statChip, { backgroundColor: COLORS.accentBg }]}>
              <Text style={[styles.statNumber, { color: COLORS.accent }]}>{inProgress}</Text>
              <Text style={[styles.statLabel, { color: COLORS.accent }]}>en curso</Text>
            </View>
          )}
          {pending > 0 && (
            <View style={[styles.statChip, { backgroundColor: '#FAEEDA' }]}>
              <Text style={[styles.statNumber, { color: '#854F0B' }]}>{pending}</Text>
              <Text style={[styles.statLabel, { color: '#854F0B' }]}>
                pendiente{pending !== 1 ? 's' : ''}
              </Text>
            </View>
          )}
        </View>
      </View>

      {/* Section header */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Tareas activas</Text>
        {tasks.length > 0 && (
          <Text style={styles.sectionCount}>{tasks.length}</Text>
        )}
      </View>

      {loading ? (
        <ActivityIndicator style={styles.loader} color={COLORS.accent} size="large" />
      ) : (
        <FlatList
          data={tasks}
          keyExtractor={item => item.id}
          renderItem={renderTask}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              colors={[COLORS.accent]}
              tintColor={COLORS.accent}
            />
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyTitle}>Todo al día</Text>
              <Text style={styles.emptySubtitle}>No tienes tareas pendientes</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: SPACING.xl,
    paddingTop: SPACING.lg,
    paddingBottom: SPACING.lg,
    backgroundColor: COLORS.surface,
    borderBottomWidth: 0.5,
    borderBottomColor: COLORS.border,
  },
  greeting: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
    marginBottom: 1,
  },
  userName: {
    fontSize: TYPOGRAPHY.title,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  statsRow: {
    flexDirection: 'row',
    gap: SPACING.xs,
  },
  statChip: {
    alignItems: 'center',
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
    borderRadius: RADIUS.md,
    minWidth: 52,
  },
  statNumber: {
    fontSize: TYPOGRAPHY.large,
    fontWeight: '700',
    lineHeight: 22,
  },
  statLabel: {
    fontSize: TYPOGRAPHY.tiny,
    fontWeight: '500',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingHorizontal: SPACING.xl,
    paddingTop: SPACING.xl,
    paddingBottom: SPACING.sm,
  },
  sectionTitle: {
    fontSize: TYPOGRAPHY.small,
    fontWeight: '600',
    color: COLORS.textSecondary,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  sectionCount: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
    backgroundColor: COLORS.surfaceAlt,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    borderRadius: RADIUS.pill,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 2,
    overflow: 'hidden',
  },
  loader: {
    flex: 1,
  },
  list: {
    paddingHorizontal: SPACING.xl,
    paddingBottom: SPACING.xxl * 2,
    gap: SPACING.sm,
  },
  taskCard: {
    flexDirection: 'row',
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    overflow: 'hidden',
  },
  accentBar: {
    width: 4,
  },
  cardBody: {
    flex: 1,
    padding: SPACING.lg,
    gap: SPACING.xs,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.xs,
  },
  typeLabel: {
    fontSize: TYPOGRAPHY.small,
    fontWeight: '700',
    letterSpacing: 0.3,
    textTransform: 'uppercase',
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
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: SPACING.sm,
  },
  detailLabel: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
    minWidth: 60,
    flexShrink: 0,
  },
  detailValue: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textPrimary,
    fontWeight: '500',
    flex: 1,
    textAlign: 'right',
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: SPACING.xs,
    gap: SPACING.sm,
  },
  taskId: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textTertiary,
    fontFamily: 'monospace',
    flex: 1,
  },
  taskDate: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
  },
  arrow: {
    fontSize: 18,
    color: COLORS.textSecondary,
    lineHeight: 20,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: SPACING.xxl * 2.5,
    gap: SPACING.sm,
  },
  emptyTitle: {
    fontSize: TYPOGRAPHY.large,
    fontWeight: '600',
    color: COLORS.textPrimary,
  },
  emptySubtitle: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
  },
});
