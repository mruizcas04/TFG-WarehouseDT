import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert, SafeAreaView, StatusBar,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import NfcManager, { NfcTech } from 'react-native-nfc-manager';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/client';
import { COLORS, TYPOGRAPHY, SPACING, RADIUS } from '../theme';

export default function SetupNFCScreen() {
  const navigation = useNavigation();
  const { user } = useAuth();

  const [locations, setLocations]           = useState([]);   // untagged locations (flat list)
  const [loading, setLoading]               = useState(true);
  const [scanningId, setScanningId]         = useState(null); // location being tagged
  const [doneCount, setDoneCount]           = useState(0);

  const nfcStarted = useRef(false);

  // Flatten warehouse full response into a list of locations with labels
  const flattenLocations = (warehouse) => {
    const result = [];
    for (const shelf of warehouse.shelves) {
      for (const level of shelf.levels) {
        for (const loc of level.locations) {
          if (!loc.nfc_tag) {
            result.push({
              id: loc.id,
              label: `Pasillo ${shelf.aisle_number} · Est. ${shelf.shelf_number} · Nivel ${level.level_number} · Pos. ${loc.position_number}`,
              aisle: shelf.aisle_number,
              shelf: shelf.shelf_number,
              level: level.level_number,
              position: loc.position_number,
            });
          }
        }
      }
    }
    return result;
  };

  const loadLocations = useCallback(async () => {
    setLoading(true);
    try {
      const warehouses = await apiFetch('/warehouses', {}, user.token);
      if (!warehouses.length) {
        Alert.alert('Sin almacén', 'No hay ningún almacén creado aún.');
        navigation.goBack();
        return;
      }
      // Use the first warehouse (most setups have one)
      const full = await apiFetch(`/warehouses/${warehouses[0].id}/full`, {}, user.token);
      setLocations(flattenLocations(full));
    } catch (e) {
      Alert.alert('Error', 'No se pudieron cargar las ubicaciones.');
    } finally {
      setLoading(false);
    }
  }, [user, navigation]);

  useEffect(() => {
    loadLocations();
    NfcManager.isSupported().then(supported => {
      if (supported && !nfcStarted.current) {
        NfcManager.start().catch(() => {});
        nfcStarted.current = true;
      }
    });
    return () => {
      NfcManager.cancelTechnologyRequest().catch(() => {});
    };
  }, [loadLocations]);

  const associateTag = async (location) => {
    setScanningId(location.id);
    try {
      await NfcManager.requestTechnology(NfcTech.NfcA);
      const tag = await NfcManager.getTag();
      await NfcManager.cancelTechnologyRequest();

      if (!tag) {
        Alert.alert('Sin respuesta', 'No se detectó ninguna etiqueta. Inténtalo de nuevo.');
        return;
      }

      const rawId = tag.id;
      const tagId = Array.isArray(rawId)
        ? rawId.map(b => b.toString(16).padStart(2, '0')).join('')
        : String(rawId);

      await apiFetch(`/locations/${location.id}/nfc`, {
        method: 'PUT',
        body: JSON.stringify({ nfc_tag: tagId }),
      }, user.token);

      // Remove from list
      setLocations(prev => prev.filter(l => l.id !== location.id));
      setDoneCount(c => c + 1);
    } catch (e) {
      const msg = e.message || '';
      if (msg.toLowerCase().includes('cancel') || msg.toLowerCase().includes('usercancel')) {
        // dismissed — do nothing
      } else {
        Alert.alert('Error', msg || 'No se pudo asociar la etiqueta.');
      }
    } finally {
      setScanningId(null);
    }
  };

  const renderLocation = ({ item }) => {
    const isScanning = scanningId === item.id;
    return (
      <View style={styles.row}>
        <View style={styles.rowInfo}>
          <Text style={styles.rowLabel}>{item.label}</Text>
          <Text style={styles.rowId}>#{item.id.split('-')[0].toUpperCase()}</Text>
        </View>
        <TouchableOpacity
          style={[styles.scanBtn, isScanning && styles.scanBtnActive]}
          onPress={() => associateTag(item)}
          disabled={scanningId !== null}
        >
          {isScanning
            ? <ActivityIndicator color={COLORS.accent} size="small" />
            : <Text style={styles.scanBtnText}>Asociar</Text>
          }
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.bg} />

      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>‹ Volver</Text>
        </TouchableOpacity>
        {doneCount > 0 && (
          <View style={styles.doneBadge}>
            <Text style={styles.doneBadgeText}>{doneCount} configuradas</Text>
          </View>
        )}
      </View>

      <View style={styles.headerSection}>
        <Text style={styles.title}>Configurar etiquetas NFC</Text>
        <Text style={styles.subtitle}>
          Toca "Asociar" en cada ubicación y acerca la etiqueta NFC al móvil para vincularla.
        </Text>
      </View>

      {loading ? (
        <ActivityIndicator style={styles.loader} color={COLORS.accent} size="large" />
      ) : locations.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyTitle}>¡Todo configurado!</Text>
          <Text style={styles.emptyText}>Todas las ubicaciones tienen etiqueta NFC asignada.</Text>
          <TouchableOpacity style={styles.primaryButton} onPress={() => navigation.goBack()}>
            <Text style={styles.primaryButtonText}>Volver</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
          <View style={styles.listHeader}>
            <Text style={styles.listHeaderText}>UBICACIONES SIN ETIQUETA</Text>
            <Text style={styles.listHeaderCount}>{locations.length}</Text>
          </View>
          <FlatList
            data={locations}
            keyExtractor={item => item.id}
            renderItem={renderLocation}
            contentContainerStyle={styles.list}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
          />
        </>
      )}

      {scanningId && (
        <View style={styles.scanningBanner}>
          <ActivityIndicator color="#fff" size="small" />
          <Text style={styles.scanningBannerText}>Acerca la etiqueta NFC al móvil...</Text>
        </View>
      )}
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
  backText: { fontSize: TYPOGRAPHY.body, color: COLORS.accent, fontWeight: '500' },
  doneBadge: {
    backgroundColor: '#EAF3DE',
    borderRadius: RADIUS.pill,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 3,
  },
  doneBadgeText: { fontSize: TYPOGRAPHY.tiny, color: '#3B6D11', fontWeight: '500' },

  headerSection: {
    paddingHorizontal: SPACING.xl,
    paddingTop: SPACING.xl,
    paddingBottom: SPACING.lg,
    borderBottomWidth: 0.5,
    borderBottomColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  title:    { fontSize: TYPOGRAPHY.title,  fontWeight: '500', color: COLORS.textPrimary, marginBottom: SPACING.xs },
  subtitle: { fontSize: TYPOGRAPHY.small, color: COLORS.textSecondary, lineHeight: 18 },

  listHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingHorizontal: SPACING.xl,
    paddingTop: SPACING.lg,
    paddingBottom: SPACING.sm,
  },
  listHeaderText:  { fontSize: TYPOGRAPHY.tiny, color: COLORS.textSecondary, fontWeight: '500', letterSpacing: 0.04 },
  listHeaderCount: { fontSize: TYPOGRAPHY.tiny, color: COLORS.textSecondary },

  list: { paddingHorizontal: SPACING.xl, paddingBottom: SPACING.xl },
  separator: { height: 0.5, backgroundColor: COLORS.border },

  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: SPACING.md,
    backgroundColor: COLORS.surface,
  },
  rowInfo:  { flex: 1 },
  rowLabel: { fontSize: TYPOGRAPHY.body, color: COLORS.textPrimary, fontWeight: '500' },
  rowId:    { fontSize: TYPOGRAPHY.tiny, color: COLORS.textSecondary, marginTop: 2, fontFamily: 'monospace' },

  scanBtn: {
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.xs + 2,
    borderRadius: RADIUS.md,
    borderWidth: 0.5,
    borderColor: COLORS.accent,
    minWidth: 72,
    alignItems: 'center',
  },
  scanBtnActive: { borderColor: COLORS.border },
  scanBtnText: { fontSize: TYPOGRAPHY.small, color: COLORS.accent, fontWeight: '500' },

  loader: { flex: 1 },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xxl,
    gap: SPACING.md,
  },
  emptyTitle: { fontSize: TYPOGRAPHY.large,  fontWeight: '500', color: COLORS.textPrimary, textAlign: 'center' },
  emptyText:  { fontSize: TYPOGRAPHY.body, color: COLORS.textSecondary, textAlign: 'center' },
  primaryButton: {
    backgroundColor: COLORS.accent,
    borderRadius: RADIUS.md,
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.xl,
    marginTop: SPACING.sm,
  },
  primaryButtonText: { color: '#fff', fontWeight: '500', fontSize: TYPOGRAPHY.body },

  scanningBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    backgroundColor: COLORS.accent,
    paddingHorizontal: SPACING.xl,
    paddingVertical: SPACING.md,
  },
  scanningBannerText: { color: '#fff', fontSize: TYPOGRAPHY.body, fontWeight: '500' },
});
