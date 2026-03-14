import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  LinearProgress,
  Box,
  Divider,
  Chip,
} from '@mui/material';
import { ExpandMore, Person, Policy, Gavel, CheckCircle } from '@mui/icons-material';
import type { DebateEntry } from '../../types';

interface QCDimension {
  label: string;
  score: number;
  reasoning: string;
}

interface QCDetailPanelProps {
  dimensions: QCDimension[];
  debateLog?: DebateEntry[];
}

function getProgressColor(score: number): 'success' | 'warning' | 'error' {
  if (score >= 80) return 'success';
  if (score >= 60) return 'warning';
  return 'error';
}

export default function QCDetailPanel({ dimensions, debateLog }: QCDetailPanelProps) {
  return (
    <Accordion
      disableGutters
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '16px !important',
        '&::before': { display: 'none' },
        backgroundColor: 'background.paper',
        overflow: 'hidden',
        transition: 'box-shadow 0.2s ease',
        '&:hover': {
          boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
        }
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMore sx={{ fontSize: 20 }} />}
        sx={{
          minHeight: 52,
          px: 2,
          '& .MuiAccordionSummary-content': { my: 1 },
        }}
      >
        <Typography variant="body2" sx={{ fontFamily: '"Google Sans", sans-serif', fontSize: 15, fontWeight: 700, color: 'text.primary', letterSpacing: '0.01em' }}>
          QC Details {debateLog && debateLog.length > 0 && " & Debate Log"}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 2, pb: 2, pt: 0 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {dimensions.map((dim) => {
            const normScore = dim.score <= 10 ? dim.score * 10 : dim.score;
            return (
              <Box
                key={dim.label}
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: 'background.default',
                  border: '1px solid',
                  borderColor: 'divider'
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ fontFamily: '"Google Sans", sans-serif', fontSize: 14, fontWeight: 700, color: 'text.primary' }}>
                    {dim.label}
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: '"Google Sans", sans-serif', fontSize: 14, fontWeight: 700, color: getProgressColor(normScore) + '.main' }}>
                    {dim.score}
                    {dim.score <= 10 && <Typography component="span" variant="caption" color="text.secondary" sx={{ fontFamily: '"Google Sans", sans-serif', fontSize: 12, ml: 0.5 }}>/ 10</Typography>}
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={normScore}
                  color={getProgressColor(normScore)}
                  sx={{ height: 6, borderRadius: 3, mb: 1, backgroundColor: 'action.hover' }}
                />
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{
                    fontFamily: '"Google Sans", sans-serif',
                    display: 'block',
                    fontSize: 13,
                    lineHeight: 1.5,
                  }}
                >
                  {dim.reasoning}
                </Typography>
              </Box>
            );
          })}

          {debateLog && debateLog.length > 0 && (
            <>
              <Divider sx={{ my: 1 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  War Room Debate
                </Typography>
              </Divider>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {debateLog.map((entry, idx) => {
                  const isDirector = entry.agent.toLowerCase().includes('director');
                  const isBrand = entry.agent.toLowerCase().includes('brand');
                  const isOrchestrator = entry.agent.toLowerCase().includes('orchestrator');
                  
                  let Icon = Person;
                  let iconColor = 'primary.main';
                  if (isDirector) { Icon = Gavel; iconColor = 'secondary.main'; }
                  if (isBrand) { Icon = Policy; iconColor = 'warning.main'; }
                  if (isOrchestrator) { Icon = CheckCircle; iconColor = 'success.main'; }

                  return (
                    <Box key={idx} sx={{ p: 1.5, borderRadius: 2, bgcolor: isOrchestrator ? 'success.light' : 'action.hover', opacity: isOrchestrator ? 0.9 : 1, border: '1px solid', borderColor: isOrchestrator ? 'success.main' : 'divider' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Icon sx={{ fontSize: 16, color: iconColor }} />
                        <Typography variant="caption" sx={{ fontWeight: 800, color: 'text.primary', textTransform: 'uppercase' }}>
                          [{entry.agent}]
                        </Typography>
                        <Chip 
                          label={entry.verdict} 
                          size="small" 
                          color={entry.verdict === 'PASS' ? 'success' : 'error'} 
                          sx={{ height: 16, fontSize: '9px', fontWeight: 900 }} 
                        />
                      </Box>
                      <Typography variant="caption" sx={{ display: 'block', fontStyle: isOrchestrator ? 'normal' : 'italic', color: 'text.primary', lineHeight: 1.4 }}>
                        {entry.reasoning}
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            </>
          )}
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}
