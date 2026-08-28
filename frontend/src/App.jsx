import { useState, useEffect, useRef, useCallback, useMemo } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

// ── High-Quality SVG Icons ───────────────────────────────────────────────────
const Icons = {
  Tooth: () => (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2c2 0 4 2 4 5 0 2.5-1 4-2 6-1 2-1 4 1 6s2 3 2 3-2 1-5 1-3-1-3-1 0-1 2-3c2-2 2-4 1-6-1-2-2-3.5-2-6 0-3 2-5 4-5z"/>
    </svg>
  ),
  Pill: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/>
      <path d="m8.5 8.5 7 7"/>
    </svg>
  ),
  ShieldAlert: () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/>
      <path d="M12 8v4"/>
      <path d="M12 16h.01"/>
    </svg>
  ),
  Search: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/>
      <path d="m21 21-4.3-4.3"/>
    </svg>
  ),
  ArrowRight: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14"/>
      <path d="m12 5 7 7-7 7"/>
    </svg>
  ),
  Filter: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
    </svg>
  ),
  Activity: () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  Sparkles: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>
    </svg>
  ),
  Info: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <path d="M12 16v-4"/>
      <path d="M12 8h.01"/>
    </svg>
  ),
  BookOpen: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
    </svg>
  )
}

// ── Quick Presets for Demo / Instant Testing ─────────────────────────────────
const PRESETS = [
  { label: 'Cardio + Antiplatelet', drugs: ['warfarin', 'atorvastatin'] },
  { label: 'Hypertension + Diabetes', drugs: ['metformin', 'lisinopril', 'aspirin'] },
  { label: 'Antidepressant + Statin', drugs: ['fluoxetine', 'simvastatin'] },
]

// ── API helpers ───────────────────────────────────────────────────────────────
async function fetchPatientDrugs() {
  const r = await fetch(`${API_BASE}/patient-drugs`)
  if (!r.ok) throw new Error('Failed to load patient drug list')
  const d = await r.json()
  return d.drugs
}

async function checkInteractions(patientDrugs) {
  const r = await fetch(`${API_BASE}/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_drugs: patientDrugs }),
  })
  if (!r.ok) throw new Error('API request failed')
  return r.json()
}

// ── Drug Search Autocomplete Component ────────────────────────────────────────
function DrugSearch({ allDrugs, selected, onAdd, onRemove, placeholder }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [focusedIdx, setFocusedIdx] = useState(0)
  const inputRef = useRef(null)
  const dropdownRef = useRef(null)

  const filtered = useMemo(() => {
    if (query.trim().length < 1) return []
    const q = query.toLowerCase().trim()
    return allDrugs
      .filter(d => d.toLowerCase().includes(q) && !selected.includes(d))
      .slice(0, 10)
  }, [query, allDrugs, selected])

  const handleSelect = (drug) => {
    onAdd(drug)
    setQuery('')
    setOpen(false)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (!open || filtered.length === 0) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setFocusedIdx(i => Math.min(i + 1, filtered.length - 1)) }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setFocusedIdx(i => Math.max(i - 1, 0)) }
    if (e.key === 'Enter')     { e.preventDefault(); handleSelect(filtered[focusedIdx]) }
    if (e.key === 'Escape')    { setOpen(false) }
  }

  useEffect(() => { setFocusedIdx(0) }, [query])

  useEffect(() => {
    const handler = (e) => {
      if (!dropdownRef.current?.contains(e.target) && e.target !== inputRef.current) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div>
      <div className="search-wrapper">
        <span className="search-prefix"><Icons.Search /></span>
        <input
          ref={inputRef}
          className="search-input-box"
          placeholder={placeholder}
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => query && setOpen(true)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          spellCheck="false"
        />
        {query && (
          <button
            className="search-clear-btn"
            onClick={() => { setQuery(''); inputRef.current?.focus() }}
            title="Clear search"
          >
            ✕
          </button>
        )}
        
        {open && query && (
          <div className="autocomplete-dropdown" ref={dropdownRef}>
            {filtered.length > 0
              ? filtered.map((drug, i) => (
                <div
                  key={drug}
                  className={`dropdown-entry${i === focusedIdx ? ' focused' : ''}`}
                  onMouseDown={() => handleSelect(drug)}
                >
                  <span className="dropdown-entry-icon"><Icons.Pill /></span>
                  <span>{drug}</span>
                </div>
              ))
              : <div className="dropdown-empty-state">No matching medication found in TWOSIDES index</div>
            }
          </div>
        )}
      </div>

      {selected.length > 0 && (
        <div className="tag-container">
          {selected.map(drug => (
            <span key={drug} className="drug-tag">
              <span>{drug}</span>
              <button
                className="drug-tag-remove"
                onClick={() => onRemove(drug)}
                title={`Remove ${drug}`}
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Interactive Result Item ───────────────────────────────────────────────────
function InteractionItem({ interaction, isOpen, onToggle, idx }) {
  const {
    dental_drug_display,
    patient_drug,
    severity_bin,
    risk_score,
    top_adverse_effects,
    n_adverse_effects,
    prr_max,
    dental_drug_category,
    dental_drug_notes,
  } = interaction

  const prrPercent = Math.min((prr_max / 50) * 100, 100)

  return (
    <div
      className={`interaction-item ${severity_bin}`}
      style={{ animationDelay: `${Math.min(idx * 0.04, 0.4)}s` }}
    >
      <div className="item-header" onClick={onToggle}>
        <span className={`tier-badge ${severity_bin}`}>{severity_bin}</span>
        
        <div className="pair-visual">
          <span className="dental-label">{dental_drug_display}</span>
          <span className="interaction-arrow"><Icons.ArrowRight /></span>
          <span className="patient-label">{patient_drug}</span>
          <span className="category-tag-mini">{dental_drug_category}</span>
        </div>

        <span className="score-badge">Score {risk_score}</span>

        <svg
          className={`chevron-arrow ${isOpen ? 'open' : ''}`}
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </div>

      {isOpen && (
        <div className="item-body">
          <div className="details-grid">
            <div className="info-pane">
              <span className="info-pane-title">
                <Icons.Activity /> Reported Adverse Reactions ({n_adverse_effects})
              </span>
              <div className="adverse-tag-list">
                {top_adverse_effects.length > 0 ? (
                  top_adverse_effects.map(ae => (
                    <span key={ae} className="adverse-tag">{ae}</span>
                  ))
                ) : (
                  <span style={{ fontSize: '13px', color: 'var(--slate-500)' }}>
                    No specific isolated reactions recorded
                  </span>
                )}
              </div>
            </div>

            <div className="info-pane">
              <span className="info-pane-title">
                <Icons.BookOpen /> Clinical Pharmacology Note
              </span>
              {dental_drug_notes ? (
                <div className="clinical-notes-box">{dental_drug_notes}</div>
              ) : (
                <div className="clinical-notes-box" style={{ color: 'var(--slate-400)' }}>
                  Standard dental prescribing guidance applies. Monitor patient for common class effects.
                </div>
              )}
            </div>
          </div>

          <div className="signal-meter-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', color: 'var(--slate-600)' }}>
              <span>Statistical Reporting Ratio (Max PRR: <strong>{prr_max.toFixed(1)}</strong>)</span>
              <span><strong>{prr_max.toFixed(0)}×</strong> elevated FAERS signal</span>
            </div>
            <div className="signal-meter-track">
              <div className="signal-meter-fill" style={{ width: `${prrPercent}%` }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main App Root ─────────────────────────────────────────────────────────────
export default function App() {
  const [allDrugs, setAllDrugs] = useState([])
  const [selectedDrugs, setSelectedDrugs] = useState([])
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [drugsLoading, setDrugsLoading] = useState(true)

  // Interactive filtering states
  const [activeTab, setActiveTab] = useState('all') // 'all' | 'major' | 'moderate' | 'minor'
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedIds, setExpandedIds] = useState(new Set())

  // Initial load
  useEffect(() => {
    fetchPatientDrugs()
      .then(setAllDrugs)
      .catch(() => setError('Could not connect to the API. Make sure the FastAPI backend is running.'))
      .finally(() => setDrugsLoading(false))
  }, [])

  const addDrug = useCallback((drug) => {
    setSelectedDrugs(prev => prev.includes(drug) ? prev : [...prev, drug])
  }, [])

  const removeDrug = useCallback((drug) => {
    setSelectedDrugs(prev => prev.filter(d => d !== drug))
  }, [])

  const applyPreset = (presetDrugs) => {
    setSelectedDrugs(presetDrugs)
  }

  const handleCheck = async () => {
    if (selectedDrugs.length === 0) return
    setLoading(true)
    setError(null)
    setResults(null)
    setActiveTab('all')
    setCategoryFilter('all')
    setSearchTerm('')
    try {
      const data = await checkInteractions(selectedDrugs)
      setResults(data)
      // Auto-expand the top 3 by default
      const initialExpanded = new Set()
      data.interactions.slice(0, 3).forEach((item) => {
        initialExpanded.add(`${item.dental_drug}-${item.patient_drug}`)
      })
      setExpandedIds(initialExpanded)
    } catch {
      setError('Failed to check interactions. Please ensure the backend API is running at http://localhost:8000.')
    } finally {
      setLoading(false)
    }
  }

  // Groupings and counts
  const majorList    = useMemo(() => results?.interactions.filter(i => i.severity_bin === 'major') ?? [], [results])
  const moderateList = useMemo(() => results?.interactions.filter(i => i.severity_bin === 'moderate') ?? [], [results])
  const minorList    = useMemo(() => results?.interactions.filter(i => i.severity_bin === 'minor') ?? [], [results])

  // Extract all distinct categories
  const availableCategories = useMemo(() => {
    if (!results) return []
    const set = new Set(results.interactions.map(i => i.dental_drug_category))
    return Array.from(set).sort()
  }, [results])

  // Filtered List based on tab, category, and inline search
  const filteredInteractions = useMemo(() => {
    if (!results) return []
    let list = results.interactions

    // Filter by tab
    if (activeTab === 'major') list = list.filter(i => i.severity_bin === 'major')
    else if (activeTab === 'moderate') list = list.filter(i => i.severity_bin === 'moderate')
    else if (activeTab === 'minor') list = list.filter(i => i.severity_bin === 'minor')

    // Filter by category
    if (categoryFilter !== 'all') {
      list = list.filter(i => i.dental_drug_category === categoryFilter)
    }

    // Filter by inline search
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase().trim()
      list = list.filter(i =>
        i.dental_drug_display.toLowerCase().includes(term) ||
        i.patient_drug.toLowerCase().includes(term) ||
        i.top_adverse_effects.some(ae => ae.toLowerCase().includes(term))
      )
    }

    return list
  }, [results, activeTab, categoryFilter, searchTerm])

  const toggleItem = (id) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (expandedIds.size > 0) {
      setExpandedIds(new Set())
    } else {
      const allIds = new Set(filteredInteractions.map(i => `${i.dental_drug}-${i.patient_drug}`))
      setExpandedIds(allIds)
    }
  }

  return (
    <>
      {/* Dynamic Animated Ambient Canvas */}
      <div className="bg-canvas">
        <div className="aurora-mesh">
          <div className="orb orb-1" />
          <div className="orb orb-2" />
          <div className="orb orb-3" />
        </div>
        <div className="floating-decorations">
          <div className="floating-icon pos-1"><Icons.Pill /></div>
          <div className="floating-icon pos-2"><Icons.Tooth /></div>
          <div className="floating-icon pos-3"><Icons.Activity /></div>
          <div className="floating-icon pos-4"><Icons.Pill /></div>
          <div className="floating-icon pos-5"><Icons.Tooth /></div>
        </div>
      </div>

      <div className="app-wrapper">
        {/* Hero Section */}
        <header className="hero">
          <div className="hero-icon-group">
            <div className="bubble pill"><Icons.Pill /></div>
            <div className="bubble tooth"><Icons.Tooth /></div>
            <div className="bubble shield"><Icons.Activity /></div>
          </div>

          <div className="hero-pill-badge">
            <span className="hero-pill-dot" />
            Clinical Pharmacology Intelligence
          </div>

          <h1>
            Dental <span className="glow-gradient">DDI</span> Risk Scorer
          </h1>

          <p className="hero-sub">
            Precision drug-drug interaction risk analytics. Input chronic medications to instantly screen 20,592 pharmacovigilance pairs for dental prescribing.
          </p>
        </header>

        {/* Disclaimer Alert */}
        <div className="disclaimer-bar">
          <div className="disclaimer-icon-box">
            <Icons.ShieldAlert />
          </div>
          <span>
            <strong>Educational & Reference Tool Only:</strong> Risk scores and reporting ratios reflect statistical FAERS signals and are not a substitute for clinical judgment or professional prescribing guidance.
          </span>
        </div>

        {/* Search Panel */}
        <div className="glass-panel">
          <div className="panel-header">
            <div className="panel-title">
              <span className="panel-title-icon"><Icons.Pill /></span>
              Patient Medication Profile
            </div>
            <div className="preset-pills-label">Quick test templates:</div>
          </div>

          {/* Quick presets */}
          <div className="quick-presets">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                className="preset-chip"
                onClick={() => applyPreset(p.drugs)}
              >
                <Icons.Sparkles /> {p.label}
              </button>
            ))}
          </div>

          <DrugSearch
            allDrugs={allDrugs}
            selected={selectedDrugs}
            onAdd={addDrug}
            onRemove={removeDrug}
            placeholder={drugsLoading ? 'Connecting to drug database…' : 'Type to search medications (e.g., Warfarin, Atorvastatin, Metformin…)'}
          />

          <button
            className="execute-btn"
            disabled={selectedDrugs.length === 0 || loading}
            onClick={handleCheck}
          >
            {loading ? (
              <div className="pulse-spinner" style={{ width: 22, height: 22, borderWidth: 2.5 }} />
            ) : (
              <>
                <Icons.Search />
                Analyze Interaction Risk ({selectedDrugs.length} Selected)
              </>
            )}
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="disclaimer-bar" style={{ background: '#fef2f2', borderColor: '#fecaca', color: '#b91c1c' }}>
            <div className="disclaimer-icon-box" style={{ background: '#fee2e2', color: '#dc2626' }}>
              <Icons.ShieldAlert />
            </div>
            <span>{error}</span>
          </div>
        )}

        {/* Results Dashboard */}
        {results && !loading && (
          <div className="results-container">
            {/* Metric KPI Cards (Clickable to switch tabs) */}
            <div className="metric-grid">
              <div
                className={`metric-card major-tier ${activeTab === 'major' ? 'active' : ''}`}
                onClick={() => setActiveTab(activeTab === 'major' ? 'all' : 'major')}
              >
                <div className="metric-data">
                  <h3>{majorList.length}</h3>
                  <span>Major Risk Pairs</span>
                </div>
                <div className="metric-icon-box" style={{ color: 'var(--major)' }}>
                  <Icons.ShieldAlert />
                </div>
              </div>

              <div
                className={`metric-card moderate-tier ${activeTab === 'moderate' ? 'active' : ''}`}
                onClick={() => setActiveTab(activeTab === 'moderate' ? 'all' : 'moderate')}
              >
                <div className="metric-data">
                  <h3>{moderateList.length}</h3>
                  <span>Moderate Risk Pairs</span>
                </div>
                <div className="metric-icon-box" style={{ color: 'var(--moderate)' }}>
                  <Icons.Activity />
                </div>
              </div>

              <div
                className={`metric-card minor-tier ${activeTab === 'minor' ? 'active' : ''}`}
                onClick={() => setActiveTab(activeTab === 'minor' ? 'all' : 'minor')}
              >
                <div className="metric-data">
                  <h3>{minorList.length}</h3>
                  <span>Minor Risk Pairs</span>
                </div>
                <div className="metric-icon-box" style={{ color: 'var(--minor)' }}>
                  <Icons.Pill />
                </div>
              </div>
            </div>

            {/* Interactive Filter Toolbar */}
            <div className="filter-toolbar">
              {/* Severity Segmented Tabs */}
              <div className="tab-pill-group">
                <button
                  className={`tab-pill-btn ${activeTab === 'all' ? 'active' : ''}`}
                  onClick={() => setActiveTab('all')}
                >
                  All Risks <span className="tab-badge">{results.total_interactions}</span>
                </button>
                <button
                  className={`tab-pill-btn ${activeTab === 'major' ? 'active' : ''}`}
                  onClick={() => setActiveTab('major')}
                >
                  🚨 Major <span className="tab-badge">{majorList.length}</span>
                </button>
                <button
                  className={`tab-pill-btn ${activeTab === 'moderate' ? 'active' : ''}`}
                  onClick={() => setActiveTab('moderate')}
                >
                  ⚠️ Moderate <span className="tab-badge">{moderateList.length}</span>
                </button>
                <button
                  className={`tab-pill-btn ${activeTab === 'minor' ? 'active' : ''}`}
                  onClick={() => setActiveTab('minor')}
                >
                  🟢 Minor <span className="tab-badge">{minorList.length}</span>
                </button>
              </div>

              {/* Secondary Controls (Category & Search) */}
              <div className="filter-right-controls">
                {/* Dental Category Selector */}
                {availableCategories.length > 1 && (
                  <select
                    className="inline-search-input"
                    style={{ width: 'auto', cursor: 'pointer', paddingRight: '24px' }}
                    value={categoryFilter}
                    onChange={e => setCategoryFilter(e.target.value)}
                  >
                    <option value="all">All Dental Drug Classes</option>
                    {availableCategories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                )}

                {/* Filter within results */}
                <div className="inline-search-box">
                  <span className="inline-search-icon"><Icons.Search /></span>
                  <input
                    className="inline-search-input"
                    placeholder="Search results..."
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                  />
                </div>

                <button className="toggle-all-btn" onClick={toggleAll}>
                  {expandedIds.size > 0 ? 'Collapse All' : 'Expand All'}
                </button>
              </div>
            </div>

            {/* Missing Drugs Warning */}
            {results.patient_drugs_not_found.length > 0 && (
              <div className="disclaimer-bar" style={{ background: '#f8fafc', borderColor: '#e2e8f0', color: '#64748b' }}>
                <Icons.Info />
                <span>
                  No interaction records found in TWOSIDES for: <strong>{results.patient_drugs_not_found.join(', ')}</strong>.
                </span>
              </div>
            )}

            {/* Interaction Card Deck */}
            {filteredInteractions.length === 0 ? (
              <div className="empty-results-card">
                <div className="empty-emoji">🔍</div>
                <h3>No interactions match the selected filters</h3>
                <p style={{ marginTop: '6px', fontSize: '14px' }}>
                  Try switching tabs or clearing your search filter.
                </p>
              </div>
            ) : (
              <div className="card-stack">
                {filteredInteractions.map((interaction, idx) => {
                  const id = `${interaction.dental_drug}-${interaction.patient_drug}`
                  return (
                    <InteractionItem
                      key={id}
                      interaction={interaction}
                      isOpen={expandedIds.has(id)}
                      onToggle={() => toggleItem(id)}
                      idx={idx}
                    />
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
