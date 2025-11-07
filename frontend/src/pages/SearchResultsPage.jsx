import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  CircularProgress,
  Pagination,
  Grid,
  Divider,
  Paper,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Slider,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';

import SearchBar from '../components/SearchBar';
import PaperCard from '../components/PaperCard';
import profileStorage from '../utils/profileStorage';
import CitationGraph from '../components/CitationGraph';
import ComparisonGraph from '../components/ComparisonGraph';


const SearchResultsPage = () => {
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const initialQuery = queryParams.get('q') || '';
  const initialSearchType = queryParams.get('type') || 'hybrid';
  
  const [query, setQuery] = useState(initialQuery);
  const [searchType, setSearchType] = useState(initialSearchType);
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareResult, setCompareResult] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [evidenceNodes, setEvidenceNodes] = useState([]);
  const [evidenceEdges, setEvidenceEdges] = useState([]);
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const [evidenceDialogOpen, setEvidenceDialogOpen] = useState(false);
  const [comparisonGraphOpen, setComparisonGraphOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const currentYear = new Date().getFullYear();
  const [yearRange, setYearRange] = useState([2000, currentYear]);
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [comparePrompt, setComparePrompt] = useState('');
  const compareColMd = Math.max(3, Math.floor(12 / Math.max(1, selected.length)));
  
  // Filter options
  const topics = ['Machine Learning', 'Natural Language Processing', 'Computer Vision', 'Robotics', 'Neuroscience'];
  
  useEffect(() => {
    const fetchPapers = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/v1/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query,
            search_type: searchType,
            limit: 10,
            page,
            filters: {
              year_from: yearRange[0],
              year_to: yearRange[1],
              topics: selectedTopics
            }
          }),
        });

        const data = await response.json();
        setPapers(Array.isArray(data.results) ? data.results : []);
        setTotalPages(Math.max(1, Math.ceil((data.count || 0) / 10)));
      } catch (error) {
        console.error('Error fetching papers:', error);
        setPapers([]);
      }
      setLoading(false);
    };

    if (query) {
      fetchPapers();
    }
  }, [query, searchType, page, selectedTopics, yearRange]);
  
  const handleSearch = (newQuery, newSearchType) => {
    // record search in profile storage
    try {
      profileStorage.addSearchHistory(newQuery);
    } catch (err) {
      console.error('Failed to add search history', err);
    }

    setQuery(newQuery);
    setSearchType(newSearchType);
    setPage(1);
    // clear selections on new search
    setSelected([]);
  };
  
  const handlePageChange = (event, value) => {
    setPage(value);
  };

  const closeCompare = () => {
    setCompareOpen(false);
    setCompareResult(null);
    setEvidenceNodes([]);
    setEvidenceEdges([]);
    setSelectedEvidence(null);
  };

  // Build a fallback evidence graph client-side when backend didn't return one
  const buildFallbackEvidenceGraph = () => {
    if (!compareResult) return { nodes: [], edges: [] };
    // Use backend evidence_graph if available and non-empty
    if (compareResult.evidence_graph && Array.isArray(compareResult.evidence_graph.edges) && compareResult.evidence_graph.edges.length > 0) {
      return compareResult.evidence_graph;
    }

    // Otherwise synthesize a simple graph from the selected papers and any metrics
    const nodes = selected.map(s => ({ id: String(s.id), title: s.title || s.name || String(s.id) }));
    const edges = [];

    // try to use metrics.embedding_similarity if available
    const metrics = compareResult.metrics || {};
    const emb = metrics.embedding_similarity || null;
    const kw = metrics.keyword_overlap || null;

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        let label = 'Semantic relation';
        let sim = null;
        let shared = [];
        if (emb && emb[i] && typeof emb[i][j] !== 'undefined') {
          sim = emb[i][j];
          label = `Semantic similarity ${sim.toFixed ? sim.toFixed(3) : String(sim)}`;
        }
        if (kw && kw[i] && typeof kw[i][j] !== 'undefined') {
          shared = []; // we don't have original keywords here, backend may supply them later
        }
        const ev = [{ ref_id: `client:semantic:${i}-${j}`, label, meta: { similarity: sim, shared_keywords: shared } }];
        edges.push({ source: nodes[i].id, target: nodes[j].id, relation: 'semantic_similarity', evidence: ev });
        edges.push({ source: nodes[j].id, target: nodes[i].id, relation: 'semantic_similarity', evidence: ev });
      }
    }
    return { nodes, edges };
  };

  const runCompare = async (prompt) => {
    setCompareLoading(true);
    try {
      // Ensure IDs are strings to satisfy backend schema
      const ids = selected.map(s => String(s.id));
      const res = await fetch('/api/ai/compare-papers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: ids, prompt })
      });
      if (!res.ok) {
        // Try to read JSON error body, fall back to status text
        let errBody = null;
        try { errBody = await res.json(); } catch (e) { /* ignore */ }
        setCompareResult({ error: errBody || res.statusText || `HTTP ${res.status}` });
      } else {
        const data = await res.json();
        setCompareResult(data);
      }
    } catch (err) {
      console.error('Compare failed', err);
      setCompareResult({ error: String(err) });
    }
    setCompareLoading(false);
  };

  // Utility: extract sentence-like points from text
  const extractPoints = (text) => {
    if (!text) return [];
    // Split on newline or sentence-ending punctuation, keep short points
    const raw = text
      .split(/\n|\r|(?<=[\.\?\!])\s+/)
      .map(s => s.trim())
      .filter(Boolean)
      .map(s => s.replace(/^[-•\s]+/, ''));
    // Filter out very short fragments
    return raw.filter(s => s.length > 20);
  };

  // Compute differences between per-paper summaries
  const computeDiffs = () => {
    if (!compareResult || !compareResult.papers) return { common: [], unique: {} };
    const per = compareResult.papers.map(p => ({ id: String(p.paper_id || p.paperId || p.paper_id || p.paper_id), text: p.summary || '' }));
    // If backend didn't return papers aligned to selected, try to use selected papers' abstracts
    const aligned = selected.map(s => {
      const found = per.find(x => x.id === String(s.id));
      return { id: String(s.id), title: s.title || s.name, text: found ? found.text : (s.abstract || s.summary || '') };
    });

    const sentenceMap = new Map();
    aligned.forEach(a => {
      const pts = extractPoints(a.text);
      pts.forEach(pt => {
        const key = pt.toLowerCase();
        if (!sentenceMap.has(key)) sentenceMap.set(key, { text: pt, papers: new Set() });
        sentenceMap.get(key).papers.add(a.id);
      });
    });

    const common = [];
    const unique = {};
    aligned.forEach(a => unique[a.id] = []);

    for (const [k, v] of sentenceMap.entries()) {
      if (v.papers.size === aligned.length) common.push(v.text);
      else if (v.papers.size === 1) {
        const only = Array.from(v.papers)[0];
        unique[only].push(v.text);
      }
    }
    return { common, unique };
  };
  
  const handleTopicChange = (topic) => {
    setSelectedTopics(prev => 
      prev.includes(topic)
        ? prev.filter(t => t !== topic)
        : [...prev, topic]
    );
    setPage(1);
  };
  
  const handleYearRangeChange = (event, newValue) => {
    setYearRange(newValue);
    setPage(1);
  };

  const handleYearFromChange = (e) => {
    const val = parseInt(e.target.value, 10);
    if (Number.isNaN(val)) return setYearRange(r => [r[0], r[1]]);
    const from = Math.max(1900, Math.min(val, yearRange[1]));
    setYearRange([from, yearRange[1]]);
    setPage(1);
  };

  const handleYearToChange = (e) => {
    const val = parseInt(e.target.value, 10);
    if (Number.isNaN(val)) return setYearRange(r => [r[0], r[1]]);
    const to = Math.min(new Date().getFullYear(), Math.max(val, yearRange[0]));
    setYearRange([yearRange[0], to]);
    setPage(1);
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <SearchBar onSearch={handleSearch} />
      </Box>
      
      {query && (
        <Typography variant="h5" gutterBottom>
          Search results for "{query}"
        </Typography>
      )}
      
      <Grid container spacing={3}>
        {/* Filters sidebar */}
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" gutterBottom>Filters</Typography>
            <Divider sx={{ mb: 2 }} />
            
            <Typography variant="subtitle2" gutterBottom>Publication Year</Typography>
            <Box sx={{ px: 1 }}>
              <Slider
                value={yearRange}
                onChange={handleYearRangeChange}
                valueLabelDisplay="auto"
                min={1900}
                max={currentYear}
              />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                <TextField 
                  size="small" 
                  label="From" 
                  type="number" 
                    value={yearRange[0]} 
                  sx={{ width: '45%' }}
                    onChange={handleYearFromChange}
                />
                <TextField 
                  size="small" 
                  label="To" 
                  type="number" 
                    value={yearRange[1]} 
                  sx={{ width: '45%' }}
                    onChange={handleYearToChange}
                />
              </Box>
            </Box>
            
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>Topics</Typography>
            <FormGroup>
              {topics.map(topic => (
                <FormControlLabel
                  key={topic}
                  control={
                    <Checkbox 
                      checked={selectedTopics.includes(topic)} 
                      onChange={() => handleTopicChange(topic)}
                      size="small"
                    />
                  }
                  label={topic}
                />
              ))}
            </FormGroup>
          </Paper>
        </Grid>
        
        {/* Search results */}
        <Grid item xs={12} md={9}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          ) : Array.isArray(papers) && papers.length > 0 ? (
            <>
              {papers.map(paper => (
                <PaperCard key={paper.id} paper={paper} selectable selected={selected.some(s => s.id === paper.id)} onToggleSelect={(p) => {
                  setSelected(prev => {
                    const exists = prev.some(x => x.id === p.id);
                    if (exists) return prev.filter(x => x.id !== p.id);
                    return [...prev, p];
                  });
                }} />
              ))}

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                <Button variant="contained" disabled={selected.length < 2} onClick={() => setCompareOpen(true)}>
                  Compare ({selected.length})
                </Button>
                {/* Persistent Evidence Graph button: always available once a compareResult exists; we synthesize a fallback graph if backend didn't provide one */}
                {compareResult ? (
                  <Button
                    variant="outlined"
                    sx={{ ml: 2 }}
                    onClick={() => { setSelectedEvidence(null); setEvidenceDialogOpen(true); }}
                  >
                    Open Evidence Graph
                  </Button>
                ) : null}
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                <Pagination 
                  count={totalPages} 
                  page={page} 
                  onChange={handlePageChange} 
                  color="primary" 
                />
              </Box>
              {/* Compare dialog */}
              <Dialog open={compareOpen} onClose={closeCompare} fullWidth maxWidth="md">
                <DialogTitle>Compare Papers ({selected.length})</DialogTitle>
                <DialogContent dividers>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    Provide an optional prompt to guide the comparison (e.g. "compare methods and datasets").
                  </Typography>
                  <TextField
                    fullWidth
                    multiline
                    minRows={2}
                    placeholder="Optional comparison prompt"
                    value={comparePrompt}
                    onChange={e => setComparePrompt(e.target.value)}
                  />

                  <Box sx={{ mt: 2 }}>
                    {compareLoading ? (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <CircularProgress size={20} />
                        <Typography>Running comparison...</Typography>
                      </Box>
                    ) : null}

                    {compareResult ? (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="subtitle1" sx={{ mb: 1 }}>Per-paper summaries</Typography>
                        {/* Differences: common and unique points */}
                        {compareResult && (
                          (() => {
                            const { common, unique } = computeDiffs();
                            return (
                              <Box sx={{ mb: 2 }}>
                                {common.length > 0 && (
                                  <Box sx={{ mb: 1 }}>
                                    <Typography variant="subtitle2">Common points</Typography>
                                    <Box component="ul" sx={{ pl: 3 }}>
                                      {common.map((c, i) => <li key={i}><Typography variant="body2">{c}</Typography></li>)}
                                    </Box>
                                  </Box>
                                )}

                                <Box>
                                  <Typography variant="subtitle2">Unique points</Typography>
                                  <Grid container spacing={1} sx={{ mt: 1 }}>
                                    {selected.map(s => (
                                      <Grid item xs={12} md={compareColMd} key={`uniq-${s.id}`}>
                                        <Paper variant="outlined" sx={{ p: 1 }}>
                                          <Typography variant="subtitle2">{s.title || s.name || 'Paper'}</Typography>
                                          <Box component="ul" sx={{ pl: 2, mb: 0 }}>
                                            {(unique[String(s.id)] || []).length > 0 ? (unique[String(s.id)] || []).map((u, i) => (
                                              <li key={i}><Typography variant="body2">{u}</Typography></li>
                                            )) : <li><Typography variant="body2">No unique points detected.</Typography></li>}
                                          </Box>
                                        </Paper>
                                      </Grid>
                                    ))}
                                  </Grid>
                                </Box>
                              </Box>
                            );
                          })()
                        )}

                        <Grid container spacing={2}>
                          {selected.map(p => {
                            const summaryObj = (compareResult.papers || []).find(x => String(x.paper_id) === String(p.id)) || {};
                            const summaryText = summaryObj.summary || p.abstract || p.summary || '(no summary available)';
                            return (
                              <Grid item xs={12} md={compareColMd} key={p.id}>
                                <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                                  <Typography variant="h6">{p.title || p.name || 'Untitled'}</Typography>
                                  {p.authors ? (
                                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                                      {Array.isArray(p.authors) ? p.authors.join(', ') : p.authors}
                                    </Typography>
                                  ) : null}
                                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{summaryText}</Typography>
                                  {p.url ? (
                                    <Box sx={{ mt: 1 }}>
                                      <Button size="small" href={p.url} target="_blank" rel="noreferrer">Open PDF</Button>
                                    </Box>
                                  ) : null}
                                </Paper>
                              </Grid>
                            );
                          })}
                        </Grid>

                        <Box sx={{ mt: 2 }}>
                          <Typography variant="subtitle1" sx={{ mb: 1 }}>Overall comparison</Typography>
                          <Paper variant="outlined" sx={{ p: 2, whiteSpace: 'pre-wrap' }}>
                            {compareResult.error
                              ? (typeof compareResult.error === 'object' ? JSON.stringify(compareResult.error, null, 2) : String(compareResult.error))
                              : (compareResult.comparison || JSON.stringify(compareResult, null, 2))}
                          </Paper>
                        </Box>

                        {/* Evidence graph control (always visible) */}
                        {/* <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Button
                            variant="outlined"
                            onClick={() => { setCompareOpen(false); setSelectedEvidence(null); setEvidenceDialogOpen(true); }}
                            disabled={!(compareResult && compareResult.evidence_graph && Array.isArray(compareResult.evidence_graph.edges) && compareResult.evidence_graph.edges.length > 0)}
                          >
                            Open Evidence Graph{compareResult && compareResult.evidence_graph && Array.isArray(compareResult.evidence_graph.edges) ? ` (${compareResult.evidence_graph.edges.length} edges)` : ''}
                          </Button>
                          {!compareResult || !compareResult.evidence_graph ? (
                            <Typography variant="caption" color="text.secondary">No evidence graph available for these papers.</Typography>
                          ) : null}
                        </Box> */}
                      </Box>
                    ) : null}
                  </Box>
                </DialogContent>
                <DialogActions>
                  <Button onClick={closeCompare}>Close</Button>
                  <Button
                    variant="contained"
                    disabled={selected.length < 2 || compareLoading}
                    onClick={() => runCompare(comparePrompt)}
                  >
                    Run Compare
                  </Button>
                  {compareResult && (
                    <Button
                      variant="outlined"
                      onClick={() => setComparisonGraphOpen(true)}
                      sx={{ ml: 1 }}
                    >
                      Show Graph
                    </Button>
                  )}
                </DialogActions>
              </Dialog>
              {/* Comparison Graph Dialog */}
              <Dialog open={comparisonGraphOpen} onClose={() => setComparisonGraphOpen(false)} fullWidth maxWidth="lg">
                <DialogTitle>Comparison Graph</DialogTitle>
                <DialogContent dividers>
                  <ComparisonGraph papers={selected} comparison={computeDiffs()} />
                </DialogContent>
                <DialogActions>
                  <Button onClick={() => setComparisonGraphOpen(false)}>Close</Button>
                </DialogActions>
              </Dialog>
              {/* Evidence Graph Dialog (separate) */}
              <Dialog open={evidenceDialogOpen} onClose={() => setEvidenceDialogOpen(false)} fullWidth maxWidth="lg">
                <DialogTitle>Evidence Graph</DialogTitle>
                <DialogContent dividers>
                  {/* Always show an evidence graph: use backend graph if present, otherwise synthesize one client-side */}
                  <Box>
                    {(() => {
                      const graph = buildFallbackEvidenceGraph();
                      return (
                        <>
                          <CitationGraph
                            nodes={graph.nodes || []}
                            edges={graph.edges || []}
                            onElementClick={(evt) => {
                              if (evt && evt.type === 'edge') {
                                const ev = evt.data && evt.data.evidence ? evt.data.evidence : null;
                                setSelectedEvidence(ev);
                              } else {
                                setSelectedEvidence(null);
                              }
                            }}
                          />

                          <Box sx={{ mt: 2 }}>
                            <Typography variant="subtitle2">Selected edge evidence</Typography>
                            <Paper variant="outlined" sx={{ p: 1, mt: 1 }}>
                              {selectedEvidence ? (
                                <Box component="ul" sx={{ pl: 3, mb: 0 }}>
                                  {selectedEvidence.map((e, i) => (
                                    <li key={i}>
                                      <Typography variant="body2">
                                        {e.label || e.ref_id}
                                        {e.meta && e.meta.title ? ` — ${e.meta.title}` : ''}
                                      </Typography>
                                    </li>
                                  ))}
                                </Box>
                              ) : (
                                <Typography variant="body2">Click an edge in the graph to view supporting references.</Typography>
                              )}
                            </Paper>
                          </Box>
                        </>
                      );
                    })()}
                  </Box>
                </DialogContent>
                <DialogActions>
                  <Button onClick={() => setEvidenceDialogOpen(false)}>Close</Button>
                </DialogActions>
              </Dialog>
            </>
          ) : query ? (
            <Typography>No results found for "{query}"</Typography>
          ) : null}
        </Grid>
      </Grid>
    </Container>
  );
};

export default SearchResultsPage;