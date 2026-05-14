import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Alert,
  ActivityIndicator, SafeAreaView, StatusBar, Animated, Easing,
  TextInput, Modal, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import NfcManager, { NfcTech, NfcEvents } from 'react-native-nfc-manager';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api/client';
import {
  COLORS, TYPE_COLORS, TYPE_LABELS,
  TYPOGRAPHY, SPACING, RADIUS,
} from '../theme';

const STEPS = {
  entrada:  ['nfc_dest',   'barcode', 'confirm'],
  salida:   ['nfc_origin', 'confirm'],
  traslado: ['nfc_origin', 'barcode', 'nfc_dest', 'confirm'],
};

const STEP_TITLES = {
  nfc_origin: 'Escanear ubicación de origen',
  nfc_dest:   'Escanear ubicación de destino',
  barcode:    'Escanear código de barras',
  confirm:    'Confirmar movimiento',
};

export default function MoveScreen() {
  const navigation = useNavigation();
  const route      = useRoute();
  const { user }   = useAuth();
  const { task }   = route.params;

  const steps = STEPS[task.type] || STEPS.entrada;
  const [stepIndex,        setStepIndex]        = useState(0);
  const [scanning,         setScanning]         = useState(false);
  const [submitting,       setSubmitting]        = useState(false);
  const [originLocation,   setOriginLocation]   = useState(null);
  const [destLocation,     setDestLocation]     = useState(null);
  const [product,          setProduct]          = useState(null);
  const [barcodeProcessed, setBarcodeProcessed] = useState(false);

  // Manual-input modal state
  const [showManual,    setShowManual]    = useState(false);
  const [manualTagId,   setManualTagId]   = useState('');
  const [manualLoading, setManualLoading] = useState(false);

  const [cameraPermission, requestCameraPermission] = useCameraPermissions();

  const pulseAnim = useRef(new Animated.Value(1)).current;
  const pulseRef  = useRef(null);
  const nfcStarted = useRef(false);

  const currentStep = steps[stepIndex];

  // Pulse animation on NFC steps
  useEffect(() => {
    if (currentStep?.startsWith('nfc')) {
      pulseRef.current = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.18, duration: 850, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1,    duration: 850, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ])
      );
      pulseRef.current.start();
    } else {
      pulseRef.current?.stop();
      pulseAnim.setValue(1);
    }
  }, [currentStep]);

  // Initialize NFC once on mount, then trigger first scan
  useEffect(() => {
    let cancelled = false;

    async function initAndScan() {
      try {
        const supported = await NfcManager.isSupported();
        if (!supported || cancelled) return;
        if (!nfcStarted.current) {
          await NfcManager.start();
          nfcStarted.current = true;
        }
        if (!cancelled && steps[0].startsWith('nfc')) {
          startNfcScan(steps[0]);
        }
      } catch {
        // NFC init failed silently — user can retry manually
      }
    }

    initAndScan();
    return () => {
      cancelled = true;
      NfcManager.cancelTechnologyRequest().catch(() => {});
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const resolveLocation = useCallback(async (tagId, step) => {
    const location = await apiFetch(`/locations/nfc/${tagId}`, {}, user.token);
    if (step === 'nfc_origin') setOriginLocation(location);
    else                       setDestLocation(location);
    setStepIndex(i => i + 1);
  }, [user]);

  const startNfcScan = useCallback(async (step) => {
    setScanning(true);
    let tagId = null;
    try {
      // NfcA reads the UID of any ISO 14443-3A tag (NTAG215, etc.) without needing NDEF data
      await NfcManager.requestTechnology(NfcTech.NfcA);
      const tag = await NfcManager.getTag();
      await NfcManager.cancelTechnologyRequest();

      if (!tag) {
        Alert.alert('Sin respuesta', 'No se detectó ninguna etiqueta NFC. Inténtalo de nuevo.');
        return;
      }

      const rawId = tag.id;
      tagId = Array.isArray(rawId)
        ? rawId.map(b => b.toString(16).padStart(2, '0')).join('')
        : String(rawId);

      await resolveLocation(tagId, step);
    } catch (e) {
      const msg = e.message || '';
      if (msg.includes('404') || msg.includes('Error 404')) {
        Alert.alert('Etiqueta no registrada', `Esta etiqueta no está asignada a ninguna ubicación.\n\nUID: ${tagId ?? 'desconocido'}\n\nCópialo y asígnalo desde el panel web → Almacén.`);
      } else if (msg.toLowerCase().includes('cancel') || msg.toLowerCase().includes('usercancel')) {
        // dismissed — stay on step
      } else if (!msg.includes('null')) {
        Alert.alert('Error NFC', msg || 'No se pudo leer la etiqueta.');
      }
    } finally {
      setScanning(false);
    }
  }, [resolveLocation]);

  // Re-trigger NFC scan when advancing to a new NFC step (not the first, handled above)
  const prevStep = useRef(null);
  useEffect(() => {
    if (currentStep?.startsWith('nfc') && prevStep.current !== null && prevStep.current !== currentStep) {
      startNfcScan(currentStep);
    }
    prevStep.current = currentStep;
  }, [currentStep, startNfcScan]);

  const handleManualSubmit = async () => {
    const tagId = manualTagId.trim();
    if (!tagId) return;
    setManualLoading(true);
    try {
      await resolveLocation(tagId, currentStep);
      setShowManual(false);
      setManualTagId('');
    } catch (e) {
      const msg = e.message || '';
      if (msg.includes('404') || msg.includes('Error 404')) {
        Alert.alert('No encontrada', 'No existe ninguna ubicación con ese ID de etiqueta.');
      } else {
        Alert.alert('Error', msg);
      }
    } finally {
      setManualLoading(false);
    }
  };

  const handleBarcodeScanned = useCallback(async ({ data }) => {
    if (barcodeProcessed) return;
    setBarcodeProcessed(true);
    try {
      const prod = await apiFetch(`/products/barcode/${encodeURIComponent(data)}`, {}, user.token);
      setProduct(prod);
      setStepIndex(i => i + 1);
    } catch {
      Alert.alert('Producto no encontrado', 'No se encontró ningún producto con ese código.');
      setBarcodeProcessed(false);
    }
  }, [barcodeProcessed, user]);

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      const body = { task_id: task.id, type: task.type };
      if (product)        body.product_id           = product.id;
      if (originLocation) body.origin_location_id    = originLocation.id;
      if (destLocation)   body.destination_location_id = destLocation.id;

      await apiFetch('/movements', { method: 'POST', body: JSON.stringify(body) }, user.token);
      await apiFetch(`/tasks/${task.id}/status`, { method: 'PUT', body: JSON.stringify({ status: 'completada' }) }, user.token);

      Alert.alert('Éxito', 'Movimiento registrado correctamente', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ]);
    } catch (e) {
      Alert.alert('Error', e.message || 'No se pudo registrar el movimiento.');
    } finally {
      setSubmitting(false);
    }
  };

  const typeColor = TYPE_COLORS[task.type] || TYPE_COLORS.entrada;

  // --- NFC step ---
  if (currentStep?.startsWith('nfc')) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="dark-content" backgroundColor={COLORS.bg} />

        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Text style={styles.backText}>‹ Volver</Text>
          </TouchableOpacity>
          <View style={[styles.badge, { backgroundColor: typeColor.bg }]}>
            <Text style={[styles.badgeText, { color: typeColor.text }]}>{TYPE_LABELS[task.type]}</Text>
          </View>
        </View>

        <View style={styles.scanContainer}>
          <Text style={styles.stepCounter}>PASO {stepIndex + 1} DE {steps.length}</Text>
          <Text style={styles.stepTitle}>{STEP_TITLES[currentStep]}</Text>

          <Animated.View style={[styles.nfcRing, { transform: [{ scale: pulseAnim }] }]}>
            <View style={styles.nfcInner}>
              <Text style={styles.nfcIcon}>📡</Text>
            </View>
          </Animated.View>

          <Text style={styles.scanHint}>
            {scanning ? 'Acerca la etiqueta NFC al dispositivo...' : 'Lector NFC listo'}
          </Text>
          {scanning
            ? <ActivityIndicator color={COLORS.accent} style={styles.scanSpinner} />
            : (
              <View style={styles.nfcActions}>
                <TouchableOpacity style={styles.primaryButton} onPress={() => startNfcScan(currentStep)}>
                  <Text style={styles.primaryButtonText}>Escanear</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.secondaryButton} onPress={() => setShowManual(true)}>
                  <Text style={styles.secondaryButtonText}>Introducir manualmente</Text>
                </TouchableOpacity>
              </View>
            )
          }
        </View>

        {/* Manual input modal */}
        <Modal visible={showManual} transparent animationType="fade">
          <KeyboardAvoidingView style={styles.modalBackdrop} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
            <View style={styles.modalCard}>
              <Text style={styles.modalTitle}>ID de etiqueta NFC</Text>
              <Text style={styles.modalHint}>Introduce el valor del campo nfc_tag de la ubicación</Text>
              <TextInput
                style={styles.modalInput}
                value={manualTagId}
                onChangeText={setManualTagId}
                placeholder="ej. 04a3f2..."
                placeholderTextColor={COLORS.textSecondary}
                autoCapitalize="none"
                autoCorrect={false}
              />
              <View style={styles.modalActions}>
                <TouchableOpacity
                  style={styles.modalCancel}
                  onPress={() => { setShowManual(false); setManualTagId(''); }}
                >
                  <Text style={styles.modalCancelText}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.primaryButton, { flex: 1 }, manualLoading && styles.primaryButtonDisabled]}
                  onPress={handleManualSubmit}
                  disabled={manualLoading}
                >
                  {manualLoading
                    ? <ActivityIndicator color="#fff" />
                    : <Text style={styles.primaryButtonText}>Confirmar</Text>
                  }
                </TouchableOpacity>
              </View>
            </View>
          </KeyboardAvoidingView>
        </Modal>
      </SafeAreaView>
    );
  }

  // --- Barcode step ---
  if (currentStep === 'barcode') {
    if (!cameraPermission?.granted) {
      return (
        <SafeAreaView style={styles.container}>
          <StatusBar barStyle="dark-content" backgroundColor={COLORS.bg} />
          <View style={styles.topBar}>
            <TouchableOpacity onPress={() => setStepIndex(i => Math.max(0, i - 1))}>
              <Text style={styles.backText}>‹ Atrás</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.scanContainer}>
            <Text style={styles.stepTitle}>Permiso de cámara necesario</Text>
            <Text style={styles.scanHint}>La app necesita acceso a la cámara para escanear códigos de barras</Text>
            <TouchableOpacity style={[styles.primaryButton, { marginTop: SPACING.lg }]} onPress={requestCameraPermission}>
              <Text style={styles.primaryButtonText}>Conceder permiso</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      );
    }

    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="dark-content" backgroundColor={COLORS.bg} />
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => setStepIndex(i => Math.max(0, i - 1))}>
            <Text style={styles.backText}>‹ Atrás</Text>
          </TouchableOpacity>
          <View style={[styles.badge, { backgroundColor: typeColor.bg }]}>
            <Text style={[styles.badgeText, { color: typeColor.text }]}>{TYPE_LABELS[task.type]}</Text>
          </View>
        </View>

        <Text style={styles.stepCounterPadded}>PASO {stepIndex + 1} DE {steps.length}</Text>
        <Text style={styles.stepTitlePadded}>{STEP_TITLES[currentStep]}</Text>

        <View style={styles.cameraContainer}>
          <CameraView
            style={styles.camera}
            facing="back"
            onBarcodeScanned={barcodeProcessed ? undefined : handleBarcodeScanned}
            barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'code128', 'qr', 'code39', 'upc_a'] }}
          />
          <View style={styles.cameraOverlay}>
            <View style={styles.scanFrame} />
          </View>
          {barcodeProcessed && (
            <View style={styles.processingOverlay}>
              <ActivityIndicator color="#fff" size="large" />
              <Text style={styles.processingText}>Buscando producto...</Text>
            </View>
          )}
        </View>

        <Text style={styles.scanHintPadded}>Apunta la cámara al código de barras del producto</Text>
      </SafeAreaView>
    );
  }

  // --- Confirm step ---
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.bg} />
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => setStepIndex(i => Math.max(0, i - 1))}>
          <Text style={styles.backText}>‹ Atrás</Text>
        </TouchableOpacity>
        <View style={[styles.badge, { backgroundColor: typeColor.bg }]}>
          <Text style={[styles.badgeText, { color: typeColor.text }]}>{TYPE_LABELS[task.type]}</Text>
        </View>
      </View>

      <View style={styles.confirmContainer}>
        <Text style={styles.stepCounter}>CONFIRMAR MOVIMIENTO</Text>
        <Text style={styles.stepTitle}>Revisa los datos</Text>

        {originLocation && (
          <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>UBICACIÓN ORIGEN</Text>
            <Text style={styles.infoValue}>Posición {originLocation.position_number}</Text>
            <Text style={styles.infoSub}>{originLocation.id.split('-')[0].toUpperCase()}</Text>
          </View>
        )}
        {destLocation && (
          <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>UBICACIÓN DESTINO</Text>
            <Text style={styles.infoValue}>Posición {destLocation.position_number}</Text>
            <Text style={styles.infoSub}>{destLocation.id.split('-')[0].toUpperCase()}</Text>
          </View>
        )}
        {product && (
          <View style={styles.infoCard}>
            <Text style={styles.infoLabel}>PRODUCTO</Text>
            <Text style={styles.infoValue}>{product.name}</Text>
            {product.description ? <Text style={styles.infoSub}>{product.description}</Text> : null}
            {product.barcode     ? <Text style={styles.infoBarcode}>{product.barcode}</Text>     : null}
          </View>
        )}

        <TouchableOpacity
          style={[styles.primaryButton, submitting && styles.primaryButtonDisabled]}
          onPress={handleConfirm}
          disabled={submitting}
        >
          {submitting
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.primaryButtonText}>Registrar movimiento</Text>
          }
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.bg },
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

  scanContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: SPACING.xxl,
  },
  stepCounter: {
    fontSize: TYPOGRAPHY.tiny,
    color: COLORS.textSecondary,
    letterSpacing: 0.05,
    marginBottom: SPACING.sm,
    textAlign: 'center',
  },
  stepTitle: {
    fontSize: TYPOGRAPHY.large,
    fontWeight: '500',
    color: COLORS.textPrimary,
    textAlign: 'center',
    marginBottom: SPACING.xxl + SPACING.lg,
  },
  nfcRing: {
    width: 160,
    height: 160,
    borderRadius: 80,
    borderWidth: 2,
    borderColor: COLORS.accent,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.xxl,
  },
  nfcInner: {
    width: 110,
    height: 110,
    borderRadius: 55,
    backgroundColor: COLORS.surface,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  nfcIcon:     { fontSize: 42 },
  scanHint:    { fontSize: TYPOGRAPHY.small, color: COLORS.textSecondary, textAlign: 'center', marginBottom: SPACING.md },
  scanSpinner: { marginTop: SPACING.sm },
  nfcActions:  { width: '100%', gap: SPACING.sm, marginTop: SPACING.md },
  primaryButton: {
    backgroundColor: COLORS.accent,
    borderRadius: RADIUS.md,
    padding: 13,
    alignItems: 'center',
  },
  primaryButtonDisabled: { backgroundColor: '#B5D4F4' },
  primaryButtonText: { color: '#fff', fontWeight: '500', fontSize: TYPOGRAPHY.body },
  secondaryButton: {
    borderRadius: RADIUS.md,
    padding: 13,
    alignItems: 'center',
    backgroundColor: COLORS.surfaceAlt,
    borderWidth: 0.5,
    borderColor: COLORS.border,
  },
  secondaryButtonText: { color: COLORS.textSecondary, fontWeight: '500', fontSize: TYPOGRAPHY.body },

  // Manual modal
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(28,28,26,0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: SPACING.xl,
  },
  modalCard: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    padding: SPACING.xl,
    width: '100%',
    borderWidth: 0.5,
    borderColor: COLORS.borderInput,
    gap: SPACING.sm,
  },
  modalTitle: { fontSize: TYPOGRAPHY.medium, fontWeight: '500', color: COLORS.textPrimary },
  modalHint:  { fontSize: TYPOGRAPHY.small,  color: COLORS.textSecondary },
  modalInput: {
    backgroundColor: COLORS.surfaceAlt,
    borderRadius: RADIUS.md,
    borderWidth: 0.5,
    borderColor: COLORS.borderInput,
    padding: SPACING.md,
    fontSize: TYPOGRAPHY.body,
    color: COLORS.textPrimary,
    fontFamily: 'monospace',
    marginTop: SPACING.xs,
  },
  modalActions: { flexDirection: 'row', gap: SPACING.sm, marginTop: SPACING.xs },
  modalCancel: {
    paddingHorizontal: SPACING.lg,
    paddingVertical: 13,
    borderRadius: RADIUS.md,
    backgroundColor: COLORS.surfaceAlt,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalCancelText: { color: COLORS.textSecondary, fontWeight: '500', fontSize: TYPOGRAPHY.body },

  // Barcode layout
  stepCounterPadded: {
    fontSize: TYPOGRAPHY.tiny, color: COLORS.textSecondary, letterSpacing: 0.05,
    paddingHorizontal: SPACING.xl, paddingTop: SPACING.lg, paddingBottom: SPACING.xs,
  },
  stepTitlePadded: {
    fontSize: TYPOGRAPHY.large, fontWeight: '500', color: COLORS.textPrimary,
    paddingHorizontal: SPACING.xl, marginBottom: SPACING.md,
  },
  cameraContainer: {
    flex: 1, marginHorizontal: SPACING.xl,
    borderRadius: RADIUS.lg, overflow: 'hidden',
  },
  camera: { flex: 1 },
  cameraOverlay: { ...StyleSheet.absoluteFillObject, justifyContent: 'center', alignItems: 'center' },
  scanFrame: {
    width: 240, height: 130,
    borderWidth: 2, borderColor: COLORS.accent,
    borderRadius: RADIUS.md, backgroundColor: 'transparent',
  },
  processingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(28,28,26,0.65)',
    justifyContent: 'center', alignItems: 'center', gap: SPACING.md,
  },
  processingText:  { color: '#fff', fontSize: TYPOGRAPHY.body },
  scanHintPadded: {
    fontSize: TYPOGRAPHY.small, color: COLORS.textSecondary, textAlign: 'center',
    paddingHorizontal: SPACING.xl, paddingVertical: SPACING.lg,
  },

  // Confirm layout
  confirmContainer: { flex: 1, padding: SPACING.xl, gap: SPACING.md },
  infoCard: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    borderWidth: 0.5,
    borderColor: COLORS.border,
    padding: SPACING.lg,
  },
  infoLabel:   { fontSize: TYPOGRAPHY.tiny,   color: COLORS.textSecondary, letterSpacing: 0.04, fontWeight: '500', marginBottom: SPACING.xs },
  infoValue:   { fontSize: TYPOGRAPHY.medium, color: COLORS.textPrimary,   fontWeight: '500' },
  infoSub:     { fontSize: TYPOGRAPHY.small,  color: COLORS.textSecondary, marginTop: 2 },
  infoBarcode: { fontSize: TYPOGRAPHY.small,  color: COLORS.textSecondary, marginTop: 2, fontFamily: 'monospace' },
});
