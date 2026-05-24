import React, { useState, useCallback } from 'react';
import {
  View, Text, FlatList, StyleSheet,
  ActivityIndicator, RefreshControl, StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/client';
import {
  COLORS, TYPE_COLORS, TYPE_LABELS,
  TYPOGRAPHY, SPACING, RADIUS, SHADOW,
} from '../theme';

function formatDateTime(dateStr) {
  const d = new Date(dateStr);
  const date = d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
  const time = d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  return { date, time };
}

function formatLocation(loc) {
  if (!loc) return null;
  const parts = [];
  if (loc.aisle_number != null) parts.push(`Pasillo ${loc.aisle_number}`);
  if (loc.shelf_number != null) parts.push(`Est. ${loc.shelf_number}`);
  if (loc.level_number != null) parts.push(`Balda ${loc.level_number}`);
  parts.push(`Hueco ${loc.position_number}`);
  return parts.join(' · ');
}

export default function HistoryScreen() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [locationsMap, setLocationsMap] = useState({});
  const [productsMap, setProductsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHistory = useCallback(async () => {
    try {
      const allTasks = await apiFetch(`/tasks/user/${user.id}`, {}, user.token);
      const completed = allTasks
        .filter(t => t.status === 'completada')
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setItems(completed);

      const locationIds = new Set();
      const productIds  = new Set();
      completed.forEach(t => {
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
      // history is supplementary — fail silently
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user]);

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchHistory();
    }, [fetchHistory])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fetchHistory();
  };

  const renderItem = ({ item, index }) => {
    const typeColor = TYPE_COLORS[item.type] || TYPE_COLORS.entrada;
    const { date, time } = formatDateTime(item.created_at);
    const originLoc = item.origin_location_id ? locationsMap[item.origin_location_id] : null;
    const destLoc   = item.destination_location_id ? locationsMap[item.destination_location_id] : null;
    const product   = item.product_id ? productsMap[item.product_id] : null;
    const isLast    = index === items.length - 1;

    let locationLine = null;
    if (item.type === 'entrada' && destLoc) {
      locationLine = formatLocation(destLoc);
    } else if (item.type === 'salida' && originLoc) {
      locationLine = formatLocation(originLoc);
    } else if (item.type === 'traslado') {
      const from = formatLocation(originLoc) ?? '—';
      const to   = formatLocation(destLoc) ?? '—';
      locationLine = `${from}  →  ${to}`;
    }

    return (
      <View style={styles.timelineRow}>
        {/* Timeline track */}
        <View style={styles.timelineTrack}>
          <View style={[styles.timelineDot, { backgroundColor: typeColor.text }]} />
          {!isLast && <View style={styles.timelineLine} />}
        </View>

        {/* Card */}
        <View style={[styles.historyCard, SHADOW.card]}>
          {/* Header: type + timestamp */}
          <View style={styles.cardHeader}>
            <Text style={[styles.typeLabel, { color: typeColor.text }]}>
              {TYPE_LABELS[item.type]}
            </Text>
            <View style={styles.timestampBlock}>
              <Text style={styles.timeText}>{time}</Text>
              <Text style={styles.dateText}>{date}</Text>
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

          <Text style={styles.taskId}>#{item.id.split('-')[0].toUpperCase()}</Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.bg} />

      <View style={styles.pageHeader}>
        <Text style={styles.pageTitle}>Historial</Text>
        {items.length > 0 && (
          <Text style={styles.countLabel}>{items.length} completada{items.length !== 1 ? 's' : ''}</Text>
        )}
      </View>

      {loading ? (
        <ActivityIndicator style={styles.loader} color={COLORS.accent} size="large" />
      ) : (
        <FlatList
          data={items}
          keyExtractor={i => i.id}
          renderItem={renderItem}
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
              <Text style={styles.emptyTitle}>Sin historial</Text>
              <Text style={styles.emptySubtitle}>Las tareas completadas aparecerán aquí</Text>
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
  pageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
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
  countLabel: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
  },
  loader: {
    flex: 1,
  },
  list: {
    paddingHorizontal: SPACING.xl,
    paddingTop: SPACING.xl,
    paddingBottom: SPACING.xxl * 2,
  },
  timelineRow: {
    flexDirection: 'row',
    gap: SPACING.md,
    marginBottom: SPACING.sm,
  },
  timelineTrack: {
    alignItems: 'center',
    width: 16,
    paddingTop: SPACING.md,
  },
  timelineDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  timelineLine: {
    flex: 1,
    width: 1.5,
    backgroundColor: COLORS.border,
    marginTop: 4,
    marginBottom: -SPACING.sm,
  },
  historyCard: {
    flex: 1,
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    padding: SPACING.md,
    gap: SPACING.xs,
    marginBottom: SPACING.sm,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 2,
  },
  typeLabel: {
    fontSize: TYPOGRAPHY.small,
    fontWeight: '700',
    letterSpacing: 0.3,
    textTransform: 'uppercase',
  },
  timestampBlock: {
    alignItems: 'flex-end',
  },
  timeText: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textPrimary,
    fontWeight: '500',
  },
  dateText: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
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
  taskId: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textTertiary,
    fontFamily: 'monospace',
    marginTop: 2,
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
    textAlign: 'center',
  },
});
