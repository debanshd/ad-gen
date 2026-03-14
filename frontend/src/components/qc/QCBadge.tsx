import { Chip } from '@mui/material';
import { CheckCircle, Warning, Error } from '@mui/icons-material';

interface QCBadgeProps {
  score: number;
  label?: string;
  isTenScale?: boolean;
}

export default function QCBadge({ score, label, isTenScale = false }: QCBadgeProps) {
  const thresholdPass = isTenScale ? 8 : 80;
  const thresholdWarn = isTenScale ? 6 : 60;
  
  const displayScore = score;

  if (score >= thresholdPass) {
    return (
      <Chip
        icon={<CheckCircle sx={{ fontSize: 16 }} />}
        label={label ? `${label}: ${displayScore}` : `Pass: ${displayScore}`}
        color="success"
        size="small"
        variant="outlined"
      />
    );
  }

  if (score >= thresholdWarn) {
    return (
      <Chip
        icon={<Warning sx={{ fontSize: 16 }} />}
        label={label ? `${label}: ${displayScore}` : `Warn: ${displayScore}`}
        color="warning"
        size="small"
        variant="outlined"
      />
    );
  }

  return (
    <Chip
      icon={<Error sx={{ fontSize: 16 }} />}
      label={label ? `${label}: ${displayScore}` : `Fail: ${displayScore}`}
      color="error"
      size="small"
      variant="outlined"
    />
  );
}
