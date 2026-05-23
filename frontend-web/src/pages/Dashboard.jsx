import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import HomeSection from './sections/HomeSection'
import WarehouseSection from './sections/WarehouseSection'
import ProductsSection from './sections/ProductsSection'
import UsersSection from './sections/UsersSection'
import TasksSection from './sections/TasksSection'
import MovementsSection from './sections/MovementsSection'

const menuItems = [
  {
    id: 'home', label: 'Inicio',
    icon: <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M1 6.5L7.5 1 14 6.5V14H9.5V10H5.5V14H1V6.5z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/></svg>
  },
  {
    id: 'warehouse', label: 'Almacén',
    icon: <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M1 4h13M1 11h13M4 1v13M11 1v13" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
  },
  {
    id: 'products', label: 'Productos',
    icon: <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><rect x="1" y="3" width="13" height="10" rx="1" stroke="currentColor" strokeWidth="1.2"/><path d="M5 3V2a2.5 2.5 0 015 0v1" stroke="currentColor" strokeWidth="1.2"/></svg>
  },
  {
    id: 'tasks', label: 'Tareas',
    icon: <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M2 7.5h11M9 3.5l4 4-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
  },
  {
    id: 'movements', label: 'Historial',
    icon: <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="7.5" cy="7.5" r="6" stroke="currentColor" strokeWidth="1.2"/><path d="M7.5 4v3.5l2 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
  },
  {
    id: 'users', label: 'Usuarios',
    icon: <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="7.5" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.2"/><path d="M2 13c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
  },
]

export default function Dashboard() {
  const [activeSection, setActiveSection] = useState('home')
  const [warehouseLoaded, setWarehouseLoaded] = useState(false)
  // { field, filter, resolve, validate }
  const [pendingLocationSelection, setPendingLocationSelection] = useState(null)
  // { locationId, locationLabel, error: string|null }
  const [selectedLocationPreview, setSelectedLocationPreview] = useState(null)
  const digitalTwinRef = useRef(null)
  const logout = useAuthStore((state) => state.logout)
  const navigate = useNavigate()

  useEffect(() => {
    if (activeSection === 'warehouse') setWarehouseLoaded(true)
  }, [activeSection])

  useEffect(() => {
    if (!pendingLocationSelection || !warehouseLoaded) return
    digitalTwinRef.current?.enterSelectionMode(pendingLocationSelection.filter)
  }, [pendingLocationSelection, warehouseLoaded])

  const handleRequestLocationSelection = (field, filter, resolve, validate) => {
    setSelectedLocationPreview(null)
    setPendingLocationSelection({ field, filter, resolve, validate })
    setWarehouseLoaded(true)
  }

  const handleLocationSelected = (locationId, locationLabel) => {
    if (!pendingLocationSelection) return
    if (selectedLocationPreview && !selectedLocationPreview.error) {
      digitalTwinRef.current?.clearSelectionHighlight(selectedLocationPreview.locationId)
    }
    const error = pendingLocationSelection.validate?.(locationId) ?? null
    if (!error) {
      digitalTwinRef.current?.highlightSelection(locationId)
      setTimeout(() => digitalTwinRef.current?.highlightSelection(locationId), 150)
    }
    setSelectedLocationPreview({ locationId, locationLabel, error })
  }

  const handleConfirmLocation = () => {
    if (!pendingLocationSelection || !selectedLocationPreview || selectedLocationPreview.error) return
    digitalTwinRef.current?.clearSelectionHighlight(selectedLocationPreview.locationId)
    digitalTwinRef.current?.exitSelectionMode()
    pendingLocationSelection.resolve(selectedLocationPreview.locationId, selectedLocationPreview.locationLabel)
    setSelectedLocationPreview(null)
    setPendingLocationSelection(null)
  }

  const handleDeselectLocation = () => {
    if (selectedLocationPreview && !selectedLocationPreview.error) {
      digitalTwinRef.current?.clearSelectionHighlight(selectedLocationPreview.locationId)
    }
    setSelectedLocationPreview(null)
  }

  const handleCancelLocationSelection = () => {
    if (selectedLocationPreview && !selectedLocationPreview.error) {
      digitalTwinRef.current?.clearSelectionHighlight(selectedLocationPreview.locationId)
    }
    digitalTwinRef.current?.exitSelectionMode()
    setSelectedLocationPreview(null)
    setPendingLocationSelection(null)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const renderSection = () => {
    switch (activeSection) {
      case 'home': return <HomeSection />
      case 'products': return <ProductsSection />
      case 'tasks': return <TasksSection onRequestLocationSelection={handleRequestLocationSelection} />
      case 'movements': return <MovementsSection />
      case 'users': return <UsersSection />
      default: return null
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#F8F8F6' }}>

      {/* Sidebar */}
      <aside style={{ width: '240px', background: 'white', borderRight: '0.5px solid #E5E4E0', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>

        {/* Logo */}
        <div style={{ padding: '20px 16px', borderBottom: '0.5px solid #E5E4E0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '32px', height: '32px', background: '#185FA5', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M1 7L8 2L15 7" stroke="white" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M1 7V14H15V7" stroke="white" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M5 14V11H11V14" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: '500', color: '#1C1C1A' }}>Warehouse DT</div>
              <div style={{ fontSize: '11px', color: '#888780', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Administración</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                padding: '9px 12px', borderRadius: '8px', border: 'none', cursor: 'pointer',
                fontSize: '13px', fontWeight: activeSection === item.id ? '500' : '400',
                background: activeSection === item.id ? '#E6F1FB' : 'transparent',
                color: activeSection === item.id ? '#185FA5' : '#5F5E5A',
                textAlign: 'left',
              }}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div style={{ padding: '12px 8px', borderTop: '0.5px solid #E5E4E0' }}>
          <button
            onClick={handleLogout}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
              padding: '9px 12px', borderRadius: '8px', border: 'none', cursor: 'pointer',
              fontSize: '13px', color: '#A32D2D', background: 'transparent', textAlign: 'left',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
              <path d="M6 13H3a1 1 0 01-1-1V3a1 1 0 011-1h3M10 10l3-2.5L10 5M13 7.5H6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '28px' }}>

          {/* WarehouseSection: siempre montada una vez cargada.
              Cuando hay pendingLocationSelection, el contenedor cambia a position:fixed
              para actuar como modal — Unity no se remonta porque es el mismo nodo DOM. */}
          {warehouseLoaded && (
            <div style={
              pendingLocationSelection
                ? {
                    position: 'fixed', top: '50%', left: '50%',
                    transform: 'translate(-50%, -50%)',
                    zIndex: 1000,
                    width: 'min(820px, calc(100vw - 32px))',
                    height: 'min(560px, calc(100vh - 60px))',
                    background: 'white', borderRadius: '16px',
                    boxShadow: '0 24px 60px rgba(0,0,0,0.28)',
                    display: 'flex', flexDirection: 'column', overflow: 'hidden',
                  }
                : { display: activeSection === 'warehouse' ? 'block' : 'none' }
            }>
              <WarehouseSection
                digitalTwinRef={digitalTwinRef}
                onLocationSelected={handleLocationSelected}
                selectionModeConfig={pendingLocationSelection}
                selectedLocationPreview={selectedLocationPreview}
                onConfirmLocation={handleConfirmLocation}
                onDeselectLocation={handleDeselectLocation}
                onCancelSelection={handleCancelLocationSelection}
              />
            </div>
          )}

          {activeSection !== 'warehouse' && renderSection()}
        </div>
      </main>

      {/* Backdrop semitransparente cuando el modal de selección está abierto */}
      {pendingLocationSelection && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 999, background: 'rgba(28,28,26,0.48)' }}
          onClick={handleCancelLocationSelection}
        />
      )}
    </div>
  )
}
