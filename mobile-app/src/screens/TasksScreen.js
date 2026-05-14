import React, { useState, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert, RefreshControl, SafeAreaView, StatusBar,
} from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/client';
import {
  COLORS, STATUS_COLORS, TYPE_COLORS, STATUS_LABELS, TYPE_LABELS,
  TYPOGRAPHY, SPACING, RADIUS,
} from '../theme';

export default function TasksScreen() {
  const { user, logout } = useAuth();
  const navigation = useNavigation();
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await apiFetch(`/tasks/user/${user.id}`, {}, user.token);
      setTasks(data);
    } catch (e) {
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
    if (task.status === 'completada') return;
    navigation.navigate('Move', { task });
  };

  const renderTask = ({ item }) => {
    const statusColor = STATUS_COLORS[item.status] || STATUS_COLORS.pendiente;
    const typeColor = TYPE_COLORS[item.type] || TYPE_COLORS.entrada;
    const date = new Date(item.created_at).toLocaleDateString('es-ES', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
    const isActionable = item.status !== 'completada';

    return (
      <TouchableOpacity
        style={[styles.taskCard, !isActionable && styles.taskCardDone]}
        onPress={() => handleTaskPress(item)}
        activeOpacity={isActionable ? 0.7 : 1}
      >
        <View style={styles.taskHeader}>
          <View style={[styles.badge, { backgroundColor: typeColor.bg }]}>
            <Text style={[styles.badgeText, { color: typeColor.text }]}>
              {TYPE_LABELS[item.type] || item.type}
            </Text>
          </View>
          <View style={[styles.badge, { backgroundColor: statusColor.bg }]}>
            <Text style={[styles.badgeText, { color: statusColor.text }]}>
              {STATUS_LABELS[item.status] || item.status}
            </Text>
          </View>
        </View>
        <View style={styles.taskFooter}>
          <Text style={styles.taskId}>#{item.id.split('-')[0].toUpperCase()}</Text>
          <Text style={styles.taskDate}>{date}</Text>
        </View>
        {isActionable && (
          <Text style={styles.taskArrow}>›</Text>
        )}
      </TouchableOpacity>
    );
  };

  const roleLabel = user.role === 'admin' ? 'Administrador' : 'Operario';
  const pending = tasks.filter(t => t.status !== 'completada').length;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.bg} />

      <View style={styles.header}>
        <View>
          <Text style={styles.headerName}>{user.name || 'Operario'}</Text>
          <Text style={styles.headerRole}>{roleLabel.toUpperCase()}</Text>
        </View>
        <View style={styles.headerActions}>
          {user.role === 'admin' && (
            <TouchableOpacity style={styles.nfcButton} onPress={() => navigation.navigate('SetupNFC')}>
              <Text style={styles.nfcButtonText}>Configurar NFC</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity style={styles.logoutButton} onPress={logout}>
            <Text style={styles.logoutText}>Salir</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Tareas asignadas</Text>
        {pending > 0 && (
          <View style={styles.countBadge}>
            <Text style={styles.countBadgeText}>{pending}</Text>
          </View>
        )}
      </View>

      {loading ? (
        <ActivityIndicator style={styles.loader} color={COLORS.accent} size="large" />
      ) : (
        <FlatList
          data={tasks}
          keyExtractor={(item) => item.id}
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
              <Text style={styles.emptyText}>No tienes tareas asignadas</Text>
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
    paddingVertical: SPACING.lg,
    borderBottomWidth: 0.5,
    borderBottomColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  headerName: {
    fontSize: TYPOGRAPHY.medium,
    fontWeight: '500',
    color: COLORS.textPrimary,
  },
  headerRole: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
    letterSpacing: 0.04,
    marginTop: 2,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
  },
  nfcButton: {
    paddingVertical: SPACING.xs,
    paddingHorizontal: SPACING.md,
    borderRadius: RADIUS.sm,
    borderWidth: 0.5,
    borderColor: COLORS.accent,
  },
  nfcButtonText: {
    color: COLORS.accent,
    fontSize: TYPOGRAPHY.small,
    fontWeight: '500',
  },
  logoutButton: {
    paddingVertical: SPACING.xs,
    paddingHorizontal: SPACING.md,
    borderRadius: RADIUS.sm,
    borderWidth: 0.5,
    borderColor: COLORS.error,
  },
  logoutText: {
    color: COLORS.error,
    fontSize: TYPOGRAPHY.small,
    fontWeight: '500',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingHorizontal: SPACING.xl,
    paddingTop: SPACING.xl,
    paddingBottom: SPACING.md,
  },
  sectionTitle: {
    fontSize: TYPOGRAPHY.medium,
    fontWeight: '500',
    color: COLORS.textPrimary,
  },
  countBadge: {
    backgroundColor: COLORS.surfaceAlt,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    borderRadius: RADIUS.pill,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 2,
  },
  countBadgeText: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
  },
  list: {
    paddingHorizontal: SPACING.xl,
    paddingBottom: SPACING.xl,
    gap: SPACING.sm,
  },
  taskCard: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    borderWidth: 0.5,
    borderColor: COLORS.border,
  },
  taskCardDone: {
    opacity: 0.45,
  },
  taskHeader: {
    flexDirection: 'row',
    gap: SPACING.sm,
    marginBottom: SPACING.md,
  },
  badge: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: 2,
    borderRadius: RADIUS.pill,
  },
  badgeText: {
    fontSize: TYPOGRAPHY.tiny,
    fontWeight: '500',
  },
  taskFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  taskId: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
    fontFamily: 'monospace',
  },
  taskDate: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
  },
  taskArrow: {
    position: 'absolute',
    right: SPACING.lg,
    top: '50%',
    fontSize: 22,
    color: COLORS.textSecondary,
  },
  loader: {
    flex: 1,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingTop: SPACING.xxl * 2,
  },
  emptyText: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
  },
});
