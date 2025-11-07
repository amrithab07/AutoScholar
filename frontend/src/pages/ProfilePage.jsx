import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Typography, 
  Paper, 
  Grid, 
  Avatar, 
  Button, 
  Tabs, 
  Tab, 
  Box,
  List,
  ListItem,
  ListItemText,
  Divider,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField
} from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import { styled } from '@mui/material/styles';

import profileStorage from '../utils/profileStorage';
import { useNavigate } from 'react-router-dom';

const ProfileAvatar = styled(Avatar)(({ theme }) => ({
  width: theme.spacing(15),
  height: theme.spacing(15),
  marginBottom: theme.spacing(2)
}));

function ProfilePage() {
  const [tabValue, setTabValue] = useState(0);
  const [profile, setProfile] = useState(() => profileStorage.getProfile());
  const [recommendations, setRecommendations] = useState({ topics: [], papers: [] });
  const navigate = useNavigate();

  const formatAuthors = (authors) => {
    if (!authors) return '';
    if (Array.isArray(authors)) {
      return authors
        .map(a => {
          if (!a) return '';
          if (typeof a === 'string') return a;
          if (typeof a === 'object') return a.name || a.full_name || a.author || a;
          return String(a);
        })
        .filter(Boolean)
        .join(', ');
    }
    if (typeof authors === 'string') return authors;
    return '';
  };

  useEffect(() => {
    // compute recommendations when profile changes
    const compute = async () => {
      const prof = profileStorage.getProfile();
      // try backend recommendations first
      try {
        const res = await fetch('/api/v1/recommendations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ saved_papers: prof.savedPapers || [], search_history: prof.searchHistory || [] })
        });
        if (res.ok) {
          const data = await res.json();
          // expect { results: [], topics: [] } or similar
          setRecommendations({ topics: data.topics || [], papers: data.results || data.papers || [] });
          return;
        }
      } catch (err) {
        // ignore and fallback to client-side
        // console.warn('Recommendation fetch failed', err);
      }

      // fallback: extract keywords from saved paper titles and recent search queries
      const texts = [];
      (prof.savedPapers || []).forEach(p => { if (p.title) texts.push(p.title); });
      (prof.searchHistory || []).slice(0, 10).forEach(h => { if (h.query) texts.push(h.query); });

      // simple tokenization & frequency
      const freq = {};
      texts.forEach(t => {
        t.split(/[^A-Za-z0-9]+/).forEach(tok => {
          const w = tok.toLowerCase();
          // exclude short/common tokens
          if (w.length > 3 && !['using','based','paper','study','approach','model','method'].includes(w)) freq[w] = (freq[w] || 0) + 1;
        });
      });
      const topics = Object.entries(freq)
        .sort((a,b) => b[1]-a[1])
        .slice(0, 8)
        .map(([k]) => k);

      // Try to fetch recommended papers by querying the search API with top topics.
      const savedIds = new Set((prof.savedPapers || []).map(p => String(p.id)));
      const candidatePapers = [];
      const topicSeeds = topics.slice(0, 4);

      try {
        const fetches = topicSeeds.map(t =>
          fetch('/api/v1/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: t, search_type: 'hybrid', limit: 6 })
          }).then(r => r.ok ? r.json() : null).catch(() => null)
        );

        const results = await Promise.all(fetches);
        results.forEach(res => {
          if (!res) return;
          const list = Array.isArray(res.results) ? res.results : (res.results || res.papers || []);
          (list || []).forEach(p => {
            const pid = String(p.id ?? p.paper_id ?? p.doi ?? p.title);
            if (!savedIds.has(pid) && !candidatePapers.some(cp => String(cp.id ?? cp.paper_id ?? cp.doi ?? cp.title) === pid)) {
              candidatePapers.push(p);
            }
          });
        });
      } catch (err) {
        // ignore network errors and fall back
      }

      // If we found candidate papers from search, use them; otherwise fallback to an empty set
      const papers = candidatePapers.slice(0, 10);

      setRecommendations({ topics, papers });
    };

    compute();
  }, [profile]);

  useEffect(() => {
    const reload = () => setProfile(profileStorage.getProfile());
    // listen for updates from storage util
    window.addEventListener('autoscolar:profileUpdated', reload);
    return () => window.removeEventListener('autoscolar:profileUpdated', reload);
  }, []);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Edit profile modal state
  const [editOpen, setEditOpen] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', institution: '', bio: '', interests: '' });
  // Novelty evaluation state
  const [noveltyOpen, setNoveltyOpen] = useState(false);
  const [draftForm, setDraftForm] = useState({ title: '', abstract: '', references: '' });
  const [noveltyLoading, setNoveltyLoading] = useState(false);
  const [noveltyResult, setNoveltyResult] = useState(null);

  const openEdit = () => {
    const p = profileStorage.getProfile();
    setForm({
      name: p.name || '',
      email: p.email || '',
      institution: p.institution || '',
      bio: p.bio || '',
      interests: (p.interests || []).join(', ')
    });
    setEditOpen(true);
  };

  const closeEdit = () => setEditOpen(false);

  const handleFormChange = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }));

  const saveProfile = () => {
    const updated = {
      id: profile.id,
      name: form.name,
      email: form.email,
      institution: form.institution,
      bio: form.bio,
      interests: form.interests.split(',').map(s => s.trim()).filter(Boolean)
    };
    profileStorage.updateProfile(updated);
    // refresh local state
    setProfile(profileStorage.getProfile());
    setEditOpen(false);
  };

  const openNovelty = () => {
    setDraftForm({ title: '', abstract: '', references: '' });
    setNoveltyResult(null);
    setNoveltyOpen(true);
  };

  const closeNovelty = () => setNoveltyOpen(false);

  const handleDraftChange = (field) => (e) => setDraftForm(f => ({ ...f, [field]: e.target.value }));

  const runNovelty = async () => {
    setNoveltyLoading(true);
    setNoveltyResult(null);
    try {
      const refs = (draftForm.references || '').split(/\n|,|;/).map(s => s.trim()).filter(Boolean);
      const res = await fetch('/api/novelty/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: draftForm.title, abstract: draftForm.abstract, references: refs })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        setNoveltyResult({ error: err.detail || err });
      } else {
        const data = await res.json();
        setNoveltyResult(data);
      }
    } catch (err) {
      setNoveltyResult({ error: String(err) });
    }
    setNoveltyLoading(false);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Grid container spacing={4}>
          <Grid item xs={12} md={4} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <ProfileAvatar src="/static/images/avatar/1.jpg" alt={profile.name || 'User'}>
              {(profile.name && profile.name.charAt(0)) || 'U'}
            </ProfileAvatar>
            <Typography variant="h5" gutterBottom>
              {profile.name || 'Your Name'}
            </Typography>
            <Typography variant="body1" color="textSecondary" gutterBottom>
              {profile.email || ''}
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              {profile.institution || ''}
            </Typography>
            <Button variant="contained" color="primary" sx={{ mt: 2 }} onClick={openEdit}>
              Edit Profile
            </Button>
            <Button variant="outlined" color="secondary" sx={{ mt: 2, ml: 1 }} onClick={() => setNoveltyOpen(true)}>
              Evaluate Draft
            </Button>
          </Grid>
          
          <Grid item xs={12} md={8}>
            <Typography variant="h6" gutterBottom>
              Bio
            </Typography>
            <Typography variant="body1" paragraph>
              {profile.bio || 'Tell others about your research interests and background.'}
            </Typography>
            
            <Typography variant="h6" gutterBottom>
              Research Interests
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 3 }}>
              {(profile.interests || []).map((interest, index) => (
                <Chip key={index} label={interest} />
              ))}
            </Box>
          </Grid>
        </Grid>
      </Paper>

      <Dialog open={editOpen} onClose={closeEdit} fullWidth maxWidth="sm">
        <DialogTitle>Edit Profile</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField label="Name" value={form.name} onChange={handleFormChange('name')} fullWidth />
            <TextField label="Email" value={form.email} onChange={handleFormChange('email')} fullWidth />
            <TextField label="Institution" value={form.institution} onChange={handleFormChange('institution')} fullWidth />
            <TextField label="Bio" value={form.bio} onChange={handleFormChange('bio')} fullWidth multiline rows={3} />
            <TextField label="Interests (comma separated)" value={form.interests} onChange={handleFormChange('interests')} fullWidth />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeEdit}>Cancel</Button>
          <Button onClick={saveProfile} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
      
      <Dialog open={noveltyOpen} onClose={closeNovelty} fullWidth maxWidth="md">
        <DialogTitle>Evaluate Draft Novelty</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField label="Title" value={draftForm.title} onChange={handleDraftChange('title')} fullWidth />
            <TextField label="Abstract / Excerpt" value={draftForm.abstract} onChange={handleDraftChange('abstract')} fullWidth multiline rows={6} />
            <TextField label="References (DOIs or titles, comma/newline separated)" value={draftForm.references} onChange={handleDraftChange('references')} fullWidth multiline rows={3} />
          </Box>

          <Box sx={{ mt: 2 }}>
            {noveltyLoading ? (
              <Typography variant="body2">Computing novelty index… this may take a few seconds.</Typography>
            ) : null}

            {noveltyResult ? (
              <Box sx={{ mt: 2 }}>
                {noveltyResult.error ? (
                  <Typography color="error">{typeof noveltyResult.error === 'object' ? JSON.stringify(noveltyResult.error) : String(noveltyResult.error)}</Typography>
                ) : (
                  <Box>
                    <Typography variant="h6">Novelty: {(noveltyResult.novelty * 100).toFixed(1)}%</Typography>
                    <Typography variant="body2" color="textSecondary">Example: "Your work has {noveltyResult.novelty} novelty in topic space; similar ideas appear in only {noveltyResult.breakdown.similar_count} prior publications."</Typography>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2">Breakdown</Typography>
                      <List>
                        <ListItem><ListItemText primary={`Max semantic similarity: ${noveltyResult.breakdown.max_similarity}`} /></ListItem>
                        <ListItem><ListItemText primary={`Similar papers >=0.7: ${noveltyResult.breakdown.similar_count}`} /></ListItem>
                        <ListItem><ListItemText primary={`Max reference overlap: ${noveltyResult.breakdown.max_overlap} (score: ${noveltyResult.breakdown.overlap_score})`} /></ListItem>
                        <ListItem><ListItemText primary={`Lexical entropy (norm): ${noveltyResult.breakdown.entropy_norm}`} /></ListItem>
                      </List>

                      <Typography variant="subtitle2">Top similar examples</Typography>
                      <List>
                        {(noveltyResult.similar_examples || []).map(ex => (
                          <ListItem key={ex.id} button onClick={() => navigate(`/search?q=${encodeURIComponent(ex.title || '')}&type=hybrid`)}>
                            <ListItemText primary={`${(ex.title||'Untitled')} — sim ${ex.similarity.toFixed(3)}`} />
                          </ListItem>
                        ))}
                        {!(noveltyResult.similar_examples || []).length && (
                          <ListItem><ListItemText primary="No similar examples returned." /></ListItem>
                        )}
                      </List>
                    </Box>
                  </Box>
                )}
              </Box>
            ) : null}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeNovelty}>Close</Button>
          <Button variant="contained" onClick={runNovelty} disabled={noveltyLoading}>Run Novelty</Button>
        </DialogActions>
      </Dialog>
      
      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="profile tabs">
            <Tab label="Saved Papers" />
            <Tab label="Search History" />
            <Tab label="Recommendations" />
          </Tabs>
        </Box>
        
        <TabPanel value={tabValue} index={0}>
          <List>
            {(profile.savedPapers || []).map((paper) => (
              <React.Fragment key={paper.id || paper.title}>
                <ListItem button>
                  <Card sx={{ width: '100%' }}>
                    <CardContent>
                      <Typography variant="h6">{paper.title}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        {formatAuthors(paper.authors)} {paper.year ? `(${paper.year})` : ''}
                      </Typography>
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                          <Button
                            startIcon={<DescriptionIcon />}
                            variant="outlined"
                            size="small"
                            sx={{ mr: 1 }}
                            href={paper.url}
                            target="_blank"
                          >
                            PDF
                          </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        </TabPanel>
        
        <TabPanel value={tabValue} index={1}>
          <List>
            {(profile.searchHistory || []).map((search) => (
              <React.Fragment key={search.id}>
                <ListItem button>
                  <ListItemText 
                    primary={search.query} 
                    secondary={`Searched on ${new Date(search.date).toLocaleString()}`} 
                  />
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        </TabPanel>
        
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Recommended Topics
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
            {(recommendations.topics || []).map((topic, i) => (
              <Button key={i} variant="outlined" size="small" onClick={() => navigate(`/search?q=${encodeURIComponent(topic)}&type=hybrid`)}>
                {topic}
              </Button>
            ))}
          </Box>

          <Typography variant="h6" gutterBottom>
            Recommended Papers
          </Typography>
          {(recommendations.papers && recommendations.papers.length > 0) ? (
            <List>
              {recommendations.papers.map((paper) => (
                <React.Fragment key={paper.id || paper.title}>
                  <ListItem button onClick={() => {
                    // navigate to search for the paper title
                    navigate(`/search?q=${encodeURIComponent(paper.title || '')}&type=hybrid`);
                  }}>
                    <Card sx={{ width: '100%' }}>
                      <CardContent>
                        <Typography variant="h6">{paper.title}</Typography>
                        <Typography variant="body2" color="textSecondary">
                            {formatAuthors(paper.authors)} {paper.year ? `(${paper.year})` : ''}
                        </Typography>
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                            <Button
                              startIcon={<DescriptionIcon />}
                              variant="outlined"
                              size="small"
                              sx={{ mr: 1 }}
                              href={paper.url}
                              target="_blank"
                            >
                              PDF
                            </Button>
                        </Box>
                      </CardContent>
                    </Card>
                  </ListItem>
                  <Divider />
                </React.Fragment>
              ))}
            </List>
          ) : (
            <Typography variant="body2">No recommendations available yet. Save some papers or do a few searches to get personalized recommendations.</Typography>
          )}
        </TabPanel>
      </Box>
    </Container>
  );
}

// TabPanel component for the tabs
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`profile-tabpanel-${index}`}
      aria-labelledby={`profile-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export default ProfilePage;