import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert, StatusBar,
  Modal, TextInput, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import NfcManager, { NfcTech } from 'react-native-nfc-manager';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/client';
import { COLORS, TYPOGRAPHY, SPACING, RADIUS } from '../theme';

export default function SetupNFCScreen() {
  const navigation = useNavigation();
  const { user } = useAuth();

  const [locations, setLocations]   = useState([]);
  const [loading, setLoading]       = useState(true);
  const [scanningId, setScanningId] = useState(null);
  const [doneCount, setDoneCount]   = useState(0);

  const [modalVisible, setModalVisible]       = useState(false);
  const [pendingLocation, setPendingLocation] = useState(null);
  const [invStep, setInvStep]                 = useState('ask');
  const [scannedProduct, setScannedProduct]   = useState(null);
  const [quantityText, setQuantityText]       = useState('');
  const [barcodeScanned, setBarcodeScanned]   = useState(false);

  const [cameraPermission, requestCameraPermission] = useCameraPermissions();

  const nfcStarted = useRef(false);

  const flattenLocations = (warehouse) => {
    const result = [];
    for (const shelf of warehouse.shelves) {
      for (const level of shelf.levels) {
        for (const loc of level.locations) {
          if (!loc.nfc_tag) {
            result.push({
              id: loc.id,
              label: `Pasillo ${shelf.aisle_number} · Est. ${shelf.shelf_number} · Balda ${level.level_number} · Hueco ${loc.position_number}`,
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
      const full = await apiFetch(`/warehouses/${warehouses[0].id}/full`, {}, user.token);
      setLocations(flattenLocations(full));
    } catch {
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

  const finishLocation = useCallback((locationId) => {
    setLocations(prev => prev.filter(l => l.id !== locationId));
    setDoneCount(c => c + 1);
    setModalVisible(false);
    setPendingLocation(null);
    setInvStep('ask');
    setScannedProduct(null);
    setQuantityText('');
    setBarcodeScanned(false);
  }, []);

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

      setPendingLocation(location);
      setInvStep('ask');
      setModalVisible(true);
    } catch (e) {
      const msg = e.message || '';
      if (msg.toLowerCase().includes('cancel') || msg.toLowerCase().includes('usercancel')) {
        // dismissed
      } else {
        Alert.alert('Error', msg || 'No se pudo asociar la etiqueta.');
      }
    } finally {
      setScanningId(null);
    }
  };

  const handleStartScan = async () => {
    if (!cameraPermission?.granted) {
      const result = await requestCameraPermission();
      if (!result.granted) {
        Alert.alert('Permiso denegado', 'Se necesita acceso a la cámara para escanear códigos de barras.');
        return;
      }
    }
    setBarcodeScanned(false);
    setInvStep('scan');
  };

  const handleBarcodeScanned = useCallback(async ({ data }) => {
    if (barcodeScanned) return;
    setBarcodeScanned(true);
    try {
      const product = await apiFetch(`/products/barcode/${data}`, {}, user.token);
      setScannedProduct(product);
      setInvStep('product');
    } catch {
      Alert.alert('Producto no encontrado', 'No existe ningún producto con ese código de barras. Inténtalo de nuevo.');
      setBarcodeScanned(false);
    }
  }, [barcodeScanned, user]);

  const handleSaveInventory = async () => {
    const qty = parseInt(quantityText, 10);
    if (!qty || qty < 1) {
      Alert.alert('Cantidad inválida', 'Introduce un número de unidades mayor que cero.');
      return;
    }
    setInvStep('saving');
    try {
      await apiFetch(`/locations/${pendingLocation.id}/inventory`, {
        method: 'POST',
        body: JSON.stringify({ product_id: scannedProduct.id, quantity: qty }),
      }, user.token);
      finishLocation(pendingLocation.id);
    } catch (e) {
      Alert.alert('Error', e.message || 'No se pudo guardar el inventario.');
      setInvStep('product');
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
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.surface} />

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

      {/* NFC scanning Modal (replaces bottom banner) */}
      <Modal visible={scanningId !== null} transparent animationType="fade">
        <View style={styles.scanModalOverlay}>
          <View style={styles.scanModalCard}>
            <ActivityIndicator color={COLORS.accent} size="large" />
            <Text style={styles.scanModalTitle}>Esperando etiqueta NFC</Text>
            <Text style={styles.scanModalText}>Acerca el móvil a la etiqueta NFC</Text>
          </View>
        </View>
      </Modal>

      {/* Inventory setup modal */}
      <Modal visible={modalVisible} transparent animationType="fade" onRequestClose={() => {}}>
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        >
          <View style={styles.modalCard}>
            {invStep === 'ask' && (
              <>
                <Text style={styles.modalTitle}>Etiqueta asociada</Text>
                <Text style={styles.modalLocation}>{pendingLocation?.label}</Text>
                <Text style={styles.modalDesc}>
                  ¿Ya hay productos almacenados en esta ubicación? Puedes registrar el inventario inicial ahora.
                </Text>
                <TouchableOpacity style={styles.primaryButton} onPress={handleStartScan}>
                  <Text style={styles.primaryButtonText}>Sí, registrar inventario</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={() => finishLocation(pendingLocation.id)}
                >
                  <Text style={styles.secondaryButtonText}>No, continuar</Text>
                </TouchableOpacity>
              </>
            )}

            {invStep === 'scan' && (
              <>
                <Text style={styles.modalTitle}>Escanear producto</Text>
                <Text style={styles.modalLocation}>{pendingLocation?.label}</Text>
                <View style={styles.cameraContainer}>
                  <CameraView
                    style={styles.camera}
                    onBarcodeScanned={barcodeScanned ? undefined : handleBarcodeScanned}
                    barcodeScannerSettings={{
                      barcodeTypes: ['ean13', 'ean8', 'code128', 'qr', 'code39', 'upc_a'],
                    }}
                  />
                </View>
                <TouchableOpacity style={styles.secondaryButton} onPress={() => setInvStep('ask')}>
                  <Text style={styles.secondaryButtonText}>Cancelar</Text>
                </TouchableOpacity>
              </>
            )}

            {invStep === 'product' && (
              <>
                <Text style={styles.modalTitle}>Producto encontrado</Text>
                <View style={styles.productCard}>
                  <Text style={styles.productName}>{scannedProduct?.name}</Text>
                  {scannedProduct?.barcode && (
                    <Text style={styles.productBarcode}>{scannedProduct.barcode}</Text>
                  )}
                </View>
                <Text style={styles.inputLabel}>Unidades en esta ubicación</Text>
                <TextInput
                  style={styles.quantityInput}
                  value={quantityText}
                  onChangeText={setQuantityText}
                  keyboardType="number-pad"
                  placeholder="0"
                  placeholderTextColor={COLORS.textSecondary}
                  autoFocus
                />
                <TouchableOpacity style={styles.primaryButton} onPress={handleSaveInventory}>
                  <Text style={styles.primaryButtonText}>Guardar inventario</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={() => { setBarcodeScanned(false); setInvStep('scan'); }}
                >
                  <Text style={styles.secondaryButtonText}>Escanear otro producto</Text>
                </TouchableOpacity>
              </>
            )}

            {invStep === 'saving' && (
              <View style={styles.savingContainer}>
                <ActivityIndicator color={COLORS.accent} size="large" />
                <Text style={styles.savingText}>Guardando inventario...</Text>
              </View>
            )}
          </View>
        </KeyboardAvoidingView>
      </Modal>
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
  title:    { fontSize: TYPOGRAPHY.title, fontWeight: '500', color: COLORS.textPrimary, marginBottom: SPACING.xs },
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
  emptyTitle: { fontSize: TYPOGRAPHY.large, fontWeight: '500', color: COLORS.textPrimary, textAlign: 'center' },
  emptyText:  { fontSize: TYPOGRAPHY.body, color: COLORS.textSecondary, textAlign: 'center' },

  primaryButton: {
    backgroundColor: COLORS.accent,
    borderRadius: RADIUS.md,
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.xl,
    alignItems: 'center',
    marginTop: SPACING.sm,
  },
  primaryButtonText: { color: '#fff', fontWeight: '500', fontSize: TYPOGRAPHY.body },

  // NFC scanning modal
  scanModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
  },
  scanModalCard: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.xl,
    padding: SPACING.xxl,
    alignItems: 'center',
    gap: SPACING.md,
    width: '85%',
    borderWidth: 0.5,
    borderColor: COLORS.border,
  },
  scanModalTitle: {
    fontSize: TYPOGRAPHY.large,
    fontWeight: '600',
    color: COLORS.textPrimary,
    textAlign: 'center',
  },
  scanModalText: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    textAlign: 'center',
  },

  // Inventory modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
  },
  modalCard: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.xl,
    padding: SPACING.xl,
    gap: SPACING.sm,
    width: '100%',
  },
  modalTitle: {
    fontSize: TYPOGRAPHY.large,
    fontWeight: '600',
    color: COLORS.textPrimary,
    marginBottom: SPACING.xs,
  },
  modalLocation: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.accent,
    fontWeight: '500',
    marginBottom: SPACING.xs,
  },
  modalDesc: {
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textSecondary,
    lineHeight: 20,
    marginBottom: SPACING.md,
  },
  secondaryButton: {
    borderRadius: RADIUS.md,
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.xl,
    alignItems: 'center',
    marginTop: SPACING.xs,
    borderWidth: 0.5,
    borderColor: COLORS.border,
  },
  secondaryButtonText: { color: COLORS.textSecondary, fontWeight: '500', fontSize: TYPOGRAPHY.body },

  cameraContainer: {
    height: 200,
    borderRadius: RADIUS.lg,
    overflow: 'hidden',
    marginVertical: SPACING.md,
  },
  camera: { flex: 1 },

  productCard: {
    backgroundColor: COLORS.bg,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    marginBottom: SPACING.sm,
    borderWidth: 0.5,
    borderColor: COLORS.border,
  },
  productName:    { fontSize: TYPOGRAPHY.body, fontWeight: '600', color: COLORS.textPrimary },
  productBarcode: { fontSize: TYPOGRAPHY.small, color: COLORS.textSecondary, fontFamily: 'monospace', marginTop: 2 },

  inputLabel: {
    fontSize: TYPOGRAPHY.small,
    color: COLORS.textSecondary,
    fontWeight: '500',
    marginBottom: SPACING.xs,
  },
  quantityInput: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    fontSize: TYPOGRAPHY.large,
    color: COLORS.textPrimary,
    textAlign: 'center',
    marginBottom: SPACING.sm,
  },

  savingContainer: {
    alignItems: 'center',
    paddingVertical: SPACING.xl,
    gap: SPACING.md,
  },
  savingText: { fontSize: TYPOGRAPHY.body, color: COLORS.textSecondary },
});
