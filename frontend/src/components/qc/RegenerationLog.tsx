import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Box,
  Chip,
  Avatar,
  Paper,
  keyframes,
} from '@mui/material';
import { 
  ExpandMore, 
  Replay, 
  Forum, 
  Movie, 
  Security, 
  Psychology, 
  FiberManualRecord 
} from '@mui/icons-material';
import type { DebateEntry } from '../../types';

const pulse = keyframes`
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
`;

interface RegenAttempt {
  attempt: number;
  scoreBefore: number;
  feedback: string;
  scoreAfter: number;
}

interface RegenerationLogProps {
  attempts?: RegenAttempt[];
  debateLog?: DebateEntry[];
}

export default function RegenerationLog({ attempts = [], debateLog = [] }: RegenerationLogProps) {
  if (attempts.length === 0 && debateLog.length === 0) return null;

  const getAgentTheme = (agent: string) => {
    const name = agent.toUpperCase();
    if (name.includes('DIRECTOR')) return { color: '#00bcd4', icon: <Movie sx={{ fontSize: 16 }} />, bg: 'rgba(0, 188, 212, 0.08)' };
    if (name.includes('BRAND')) return { color: '#e91e63', icon: <Security sx={{ fontSize: 16 }} />, bg: 'rgba(233, 30, 99, 0.08)' };
    if (name.includes('ORCHESTRATOR')) return { color: '#9c27b0', icon: <Psychology sx={{ fontSize: 18 }} />, bg: 'rgba(156, 39, 176, 0.12)' };
    return { color: '#9e9e9e', icon: <Forum sx={{ fontSize: 16 }} />, bg: 'rgba(158, 158, 158, 0.08)' };
  };

  return (
    <Accordion
      disableGutters
      elevation={0}
      defaultExpanded={debateLog.length > 0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '8px !important',
        backgroundColor: '#fff',
        overflow: 'hidden',
        mb: 2,
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMore sx={{ fontSize: 18 }} />}
        sx={{
          minHeight: 48,
          px: 2,
          backgroundColor: 'rgba(0,0,0,0.01)',
          borderBottom: '1px solid',
          borderColor: 'divider',
          '& .MuiAccordionSummary-content': { my: 1, alignItems: 'center', gap: 1 },
        }}
      >
        {debateLog.length > 0 ? (
          <Forum color="primary" sx={{ fontSize: 20 }} />
        ) : (
          <Replay sx={{ fontSize: 18, color: 'text.secondary' }} />
        )}
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, letterSpacing: -0.2 }}>
            {debateLog.length > 0 ? 'Multi-Agent QC Debate' : 'Regeneration History'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {debateLog.length > 0 
              ? `${debateLog.length} rounds of analysis` 
              : `${attempts.length} refinement attempt${attempts.length > 1 ? 's' : ''}`}
          </Typography>
        </Box>
        
        {debateLog.length > 0 && (
          <Chip 
            icon={<FiberManualRecord sx={{ animation: `${pulse} 2s infinite ease-in-out`, fontSize: '10px !important' }} />}
            label="LIVE WAR ROOM" 
            size="small" 
            color="primary"
            sx={{ height: 20, fontSize: 10, fontWeight: 800, px: 0.5 }}
          />
        )}
      </AccordionSummary>
      <AccordionDetails sx={{ p: 2, backgroundColor: '#fafafa' }}>
        {/* Debate Log Rendering */}
        {debateLog.length > 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {debateLog.map((entry, i) => {
              const theme = getAgentTheme(entry.agent);
              return (
                <Box key={i} sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                  <Avatar 
                    sx={{ 
                      width: 32, 
                      height: 32, 
                      bgcolor: theme.color,
                      boxShadow: '0 2px 4px rgba(0,0,0,0.1)' 
                    }}
                  >
                    {theme.icon}
                  </Avatar>
                  <Paper 
                    elevation={0}
                    sx={{ 
                      p: 1.5, 
                      flexGrow: 1, 
                      borderRadius: '0 12px 12px 12px',
                      border: '1px solid',
                      borderColor: 'divider',
                      backgroundColor: theme.bg,
                      position: 'relative',
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.75 }}>
                      <Typography variant="caption" sx={{ fontWeight: 800, color: theme.color, textTransform: 'uppercase', fontSize: 10 }}>
                        {entry.agent}
                      </Typography>
                      {entry.verdict && (
                        <Chip 
                          label={entry.verdict} 
                          size="small" 
                          sx={{ 
                            height: 18, 
                            fontSize: 9, 
                            fontWeight: 800,
                            bgcolor: entry.verdict.toLowerCase().includes('pass') ? 'success.main' : 'warning.main',
                            color: '#fff',
                            px: 0.5
                          }} 
                        />
                      )}
                    </Box>
                    <Typography variant="body2" sx={{ fontSize: 13, color: 'text.primary', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                      {entry.reasoning}
                    </Typography>
                  </Paper>
                </Box>
              );
            })}
          </Box>
        )}

        {/* Regeneration Attempts Rendering */}
        {attempts.length > 0 && (
          <Box sx={{ mt: debateLog.length > 0 ? 3 : 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
            {debateLog.length > 0 && <Typography variant="caption" sx={{ fontWeight: 700, color: 'text.disabled', textAlign: 'center', display: 'block' }}>REGENERATION STEPS</Typography>}
            {attempts.map((attempt) => (
              <Paper 
                key={attempt.attempt}
                elevation={0}
                sx={{ p: 1.5, borderLeft: '3px solid', borderColor: 'primary.main', bgcolor: '#fff' }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    Refinement #{attempt.attempt}
                  </Typography>
                  <Chip
                    label={`${attempt.scoreBefore} → ${attempt.scoreAfter}`}
                    size="small"
                    color={attempt.scoreAfter > attempt.scoreBefore ? 'success' : 'warning'}
                    sx={{ height: 20, fontSize: 10, fontWeight: 700 }}
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12 }}>
                  {attempt.feedback}
                </Typography>
              </Paper>
            ))}
          </Box>
        )}
      </AccordionDetails>
    </Accordion>
  );
}
