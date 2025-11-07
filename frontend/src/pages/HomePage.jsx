import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Button,
  Grid,
  Paper
} from '@mui/material';
import TextField from '@mui/material/TextField';
import CitationGraph from '../components/CitationGraph';
import { useState } from 'react';
import SearchIcon from '@mui/icons-material/Search';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import FormatQuoteIcon from '@mui/icons-material/FormatQuote';

import SearchBar from '../components/SearchBar';

const HomePage = () => {
  const navigate = useNavigate();
  const [graphPaperId, setGraphPaperId] = useState('');
  const [graphNodes, setGraphNodes] = useState([]);
  const [graphEdges, setGraphEdges] = useState([]);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState(null);

  const handleSearch = (query, searchType) => {
    navigate(`/search?q=${encodeURIComponent(query)}&type=${searchType}`);
  };

  const features = [
    {
      icon: <SearchIcon fontSize="large" color="primary" />,
      title: 'Hybrid Search',
      description: 'Combines traditional keyword search with semantic understanding for more accurate results.'
    },
    {
      icon: <AutoAwesomeIcon fontSize="large" color="primary" />,
      title: 'AI Summaries',
      description: 'Get AI-generated summaries of research papers to quickly understand key findings.'
    },
    {
      icon: <TrendingUpIcon fontSize="large" color="primary" />,
      title: 'Personalized Recommendations',
      description: 'Discover relevant papers based on your research interests and reading history.'
    },
    {
      icon: <FormatQuoteIcon fontSize="large" color="primary" />,
      title: 'Citation Management',
      description: 'Easily generate and export citations in multiple formats for your research.'
    }
  ];

  const trendingTopics = [
    'Machine Learning',
    'Climate Change',
    'Quantum Computing',
    'Renewable Energy',
    'Artificial Intelligence',
    'Genomics'
  ];

  return (
    <Box>
      {/* Hero Section */}
      <Box
        sx={{
          bgcolor: 'primary.main',
          color: 'white',
          py: 8,
          mb: 6,
          borderRadius: { xs: 0, md: 2 },
          boxShadow: 3
        }}
      >
        <Container maxWidth="lg">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={7}>
              <Typography variant="h2" component="h1" gutterBottom fontWeight="bold">
                Discover Research Papers with AI
              </Typography>
              <Typography variant="h5" paragraph>
                AutoScholar helps you find, understand, and cite academic papers using advanced AI technology.
              </Typography>
              <Box sx={{ mt: 4 }}>
                <SearchBar onSearch={handleSearch} />
              </Box>
            </Grid>
            <Grid item xs={12} md={5} sx={{ display: { xs: 'none', md: 'block' } }}>
              <Box
                component="img"
                src="/autocholar.png"
                alt="AutoScholar"
                sx={{
                  width: '100%',
                  borderRadius: 2,
                  boxShadow: 3
                }}
              />
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Knowledge Graph Panel */}
      <Container maxWidth="lg" sx={{ mb: 8 }}>
        <Typography variant="h4" component="h2" gutterBottom>
          Knowledge Graph
        </Typography>
        <Paper sx={{ p: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Paper ID or DOI"
                value={graphPaperId}
                onChange={(e) => setGraphPaperId(e.target.value)}
                placeholder="Enter paper id or DOI (e.g. 10.1000/xyz)"
              />
            </Grid>
            <Grid item>
              <Button variant="contained" onClick={async () => {
                if (!graphPaperId) return setGraphError('Enter a paper id');
                setGraphLoading(true); setGraphError(null);
                try {
                  const res = await fetch(`/api/graph/citations?paper_id=${encodeURIComponent(graphPaperId)}`);
                  if (!res.ok) {
                    const err = await res.json().catch(() => ({ detail: res.statusText }));
                    setGraphError(err.detail || res.statusText);
                    setGraphNodes([]); setGraphEdges([]);
                  } else {
                    const data = await res.json();
                    setGraphNodes(data.nodes || []);
                    setGraphEdges(data.edges || []);
                  }
                } catch (err) {
                  setGraphError(String(err));
                }
                setGraphLoading(false);
              }}>Show citing papers</Button>
            </Grid>
            <Grid item>
              <Button variant="outlined" onClick={async () => {
                if (!graphPaperId) return setGraphError('Enter a paper id');
                setGraphLoading(true); setGraphError(null);
                try {
                  const res = await fetch(`/api/graph/similar?paper_id=${encodeURIComponent(graphPaperId)}`);
                  if (!res.ok) {
                    const err = await res.json().catch(() => ({ detail: res.statusText }));
                    setGraphError(err.detail || res.statusText);
                    setGraphNodes([]); setGraphEdges([]);
                  } else {
                    const data = await res.json();
                    setGraphNodes(data.nodes || []);
                    setGraphEdges(data.edges || []);
                  }
                } catch (err) {
                  setGraphError(String(err));
                }
                setGraphLoading(false);
              }}>Show similar papers</Button>
            </Grid>
          </Grid>

          <Box sx={{ mt: 3 }}>
            {graphError && <Typography color="error" sx={{ mb: 1 }}>{String(graphError)}</Typography>}
            {graphLoading && <Typography variant="body2">Loading graph…</Typography>}
            <CitationGraph nodes={graphNodes} edges={graphEdges} onNodeClick={(data) => {
              // clicking a node will load its citing papers
              if (data && data.id) {
                setGraphPaperId(String(data.id));
                // auto-load citing papers for clicked node
                (async () => {
                  setGraphLoading(true); setGraphError(null);
                  try {
                    const res = await fetch(`/api/graph/citations?paper_id=${encodeURIComponent(String(data.id))}`);
                    if (!res.ok) {
                      const err = await res.json().catch(() => ({ detail: res.statusText }));
                      setGraphError(err.detail || res.statusText);
                    } else {
                      const d = await res.json();
                      setGraphNodes(d.nodes || []);
                      setGraphEdges(d.edges || []);
                    }
                  } catch (err) {
                    setGraphError(String(err));
                  }
                  setGraphLoading(false);
                })();
              }
            }} />
          </Box>
        </Paper>
      </Container>

      {/* CTA Section */}
      <Container maxWidth="md" sx={{ mb: 8 }}>
        <Paper
          sx={{
            p: 4,
            textAlign: 'center',
            borderRadius: 2,
            bgcolor: 'primary.light',
            color: 'primary.contrastText'
          }}
        >
          <Typography variant="h5" component="h3" gutterBottom>
            Ready to enhance your research?
          </Typography>
          <Typography variant="body1" paragraph>
            Join thousands of researchers using AutoScholar to discover and understand academic papers.
          </Typography>
          <Button
            variant="contained"
            color="secondary"
            size="large"
            sx={{ mt: 2, borderRadius: 2, px: 4 }}
          >
            Sign Up Now
          </Button>
        </Paper>
      </Container>
    </Box>
  );
};

export default HomePage;