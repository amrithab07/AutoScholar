import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Chip,
  Button,
  Divider,
  CircularProgress,
  Card,
  CardContent,
  Tabs,
  Tab,
  TextField,
  IconButton
} from '@mui/material';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import DownloadIcon from '@mui/icons-material/Download';
import ShareIcon from '@mui/icons-material/Share';
import FormatQuoteIcon from '@mui/icons-material/FormatQuote';
import SendIcon from '@mui/icons-material/Send';

// Mock data - would be replaced with API calls
const mockPaper = {
  id: '1',
  title: 'Attention Is All You Need',
  authors: [
    { id: '1', name: 'Ashish Vaswani', affiliation: 'Google Brain' },
    { id: '2', name: 'Noam Shazeer', affiliation: 'Google Brain' },
    { id: '3', name: 'Niki Parmar', affiliation: 'Google Research' },
    { id: '4', name: 'Jakob Uszkoreit', affiliation: 'Google Research' },
    { id: '5', name: 'Llion Jones', affiliation: 'Google Research' },
    { id: '6', name: 'Aidan N. Gomez', affiliation: 'University of Toronto' },
    { id: '7', name: 'Łukasz Kaiser', affiliation: 'Google Brain' },
    { id: '8', name: 'Illia Polosukhin', affiliation: 'Google Brain' }
  ],
  journal: 'Advances in Neural Information Processing Systems',
  publication_date: '2017-06-12',
  citation_count: 45000,
  abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data.',
  keywords: ['Deep Learning', 'NLP', 'Transformers', 'Attention Mechanism', 'Neural Networks', 'Machine Translation'],
  ai_summary: 'This groundbreaking paper introduces the Transformer architecture that relies entirely on self-attention mechanisms without using recurrence or convolution, achieving state-of-the-art results on machine translation tasks while being more parallelizable and requiring less training time. The architecture has become the foundation for many modern NLP models including BERT, GPT, and T5.',
  pdf_url: '#',
  doi: '10.48550/arXiv.1706.03762',
  references: [
    { id: 'ref1', title: 'Neural Machine Translation by Jointly Learning to Align and Translate', authors: 'Bahdanau et al.', year: '2014' },
    { id: 'ref2', title: 'Sequence to Sequence Learning with Neural Networks', authors: 'Sutskever et al.', year: '2014' },
    { id: 'ref3', title: 'Convolutional Sequence to Sequence Learning', authors: 'Gehring et al.', year: '2017' }
  ],
  citations: [
    { id: 'cite1', title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding', authors: 'Devlin et al.', year: '2018' },
    { id: 'cite2', title: 'Language Models are Few-Shot Learners', authors: 'Brown et al.', year: '2020' },
    { id: 'cite3', title: 'Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer', authors: 'Raffel et al.', year: '2019' }
  ]
};

const PaperDetailPage = () => {
  const { id } = useParams();
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [question, setQuestion] = useState('');

  useEffect(() => {
    const fetchPaper = async () => {
      setLoading(true);
      
      // In a real app, this would be an API call
      // const response = await api.getPaper(id);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setPaper(mockPaper);
      setLoading(false);
    };
    
    fetchPaper();
  }, [id]);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleSaveClick = () => {
    setSaved(!saved);
  };

  const handleQuestionSubmit = (e) => {
    e.preventDefault();
    if (question.trim()) {
      // In a real app, this would send the question to the API
      console.log('Question submitted:', question);
      setQuestion('');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!paper) {
    return (
      <Container>
        <Typography variant="h5">Paper not found</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            {paper.title}
          </Typography>
          <IconButton onClick={handleSaveClick} aria-label="save paper">
            {saved ? <BookmarkIcon color="primary" fontSize="large" /> : <BookmarkBorderIcon fontSize="large" />}
          </IconButton>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1">
            {paper.authors.map((author, index) => (
              <React.Fragment key={author.id}>
                <span>{author.name}</span>
                {index < paper.authors.length - 1 && ', '}
              </React.Fragment>
            ))}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {paper.journal} • {new Date(paper.publication_date).getFullYear()} • {paper.citation_count} citations
          </Typography>
          {paper.doi && (
            <Typography variant="body2" color="text.secondary">
              DOI: {paper.doi}
            </Typography>
          )}
        </Box>

        <Box sx={{ mb: 3, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {paper.keywords.map((keyword, index) => (
            <Chip key={index} label={keyword} size="small" />
          ))}
        </Box>

        <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
          <Button variant="contained" startIcon={<DownloadIcon />} href={paper.pdf_url} target="_blank">
            Download PDF
          </Button>
          <Button variant="outlined" startIcon={<FormatQuoteIcon />}>
            Cite
          </Button>
          <Button variant="outlined" startIcon={<ShareIcon />}>
            Share
          </Button>
        </Box>

        <Divider sx={{ mb: 3 }} />

        <Box sx={{ mb: 3 }}>
          <Tabs value={activeTab} onChange={handleTabChange} aria-label="paper details tabs">
            <Tab label="Abstract" />
            <Tab label="AI Summary" />
            <Tab label="References" />
            <Tab label="Citations" />
            <Tab label="Ask Questions" />
          </Tabs>
          
          <Box sx={{ mt: 2 }}>
            {activeTab === 0 && (
              <Typography variant="body1" paragraph>
                {paper.abstract}
              </Typography>
            )}
            
            {activeTab === 1 && (
              <Typography variant="body1" paragraph>
                {paper.ai_summary}
              </Typography>
            )}
            
            {activeTab === 2 && (
              <Grid container spacing={2}>
                {paper.references.map(ref => (
                  <Grid item xs={12} key={ref.id}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1">{ref.title}</Typography>
                        <Typography variant="body2">{ref.authors} ({ref.year})</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
            
            {activeTab === 3 && (
              <Grid container spacing={2}>
                {paper.citations.map(citation => (
                  <Grid item xs={12} key={citation.id}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1">{citation.title}</Typography>
                        <Typography variant="body2">{citation.authors} ({citation.year})</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
            
            {activeTab === 4 && (
              <Box>
                <Typography variant="body1" paragraph>
                  Ask questions about this paper and get AI-powered answers.
                </Typography>
                <Box component="form" onSubmit={handleQuestionSubmit} sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    variant="outlined"
                    placeholder="Ask a question about this paper..."
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                  />
                  <Button 
                    type="submit" 
                    variant="contained" 
                    endIcon={<SendIcon />}
                    disabled={!question.trim()}
                  >
                    Ask
                  </Button>
                </Box>
              </Box>
            )}
          </Box>
        </Box>
      </Paper>

      <Typography variant="h5" gutterBottom>
        Related Papers
      </Typography>
      <Grid container spacing={2}>
        {[1, 2, 3].map(i => (
          <Grid item xs={12} md={4} key={i}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom noWrap>
                  Related Paper Title {i}
                </Typography>
                <Typography variant="body2" color="text.secondary" noWrap>
                  Author 1, Author 2, et al.
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Journal Name • 2022 • 1000 citations
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default PaperDetailPage;