
import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Slider,
  IconButton,
  Button,
  Chip,
  Tooltip,
  LinearProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  SkipNext as NextIcon,
  SkipPrevious as PrevIcon,
  Speed as SpeedIcon,
  CalendarToday as CalendarIcon,
  Timeline as TimelineIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';

// Types
interface ConstructionTask {
  id: string;
  name: string;
  elementIds: string[];
  startDate: string;
  endDate: string;
  duration: number; // days
  progress: number; // 0-100
  color: string;
  dependencies: string[];
  trade: string;
}

interface Timeline4DProps {
  tasks: ConstructionTask[];
  currentDate?: string;
  onDateChange?: (date: string) => void;
  onTaskSelect?: (task: ConstructionTask) => void;
  onTaskVisibilityChange?: (taskId: string, visible: boolean) => void;
  onTaskProgressChange?: (taskId: string, progress: number) => void;
  playbackSpeed?: number;
}

const PLAYBACK_SPEEDS = [0.5, 1, 2, 5, 10];

export const Timeline4D: React.FC<Timeline4DProps> = ({
  tasks,
  currentDate,
  onDateChange,
  onTaskSelect,
  onTaskVisibilityChange,
  onTaskProgressChange,
  playbackSpeed = 1,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentProgress, setCurrentProgress] = useState(0);
  const [speed, setSpeed] = useState(playbackSpeed);
  const [selectedTask, setSelectedTask] = useState<ConstructionTask | null>(null);
  const [showTaskDialog, setShowTaskDialog] = useState(false);
  const [visibleTasks, setVisibleTasks] = useState<Set<string>>(new Set(tasks.map((t) => t.id)));
  const animationRef = useRef<number>();

  // Calculate timeline bounds
  const timelineBounds = React.useMemo(() => {
    if (tasks.length === 0) return { start: new Date(), end: new Date(), duration: 0 };

    const dates = tasks.flatMap((t) => [new Date(t.startDate), new Date(t.endDate)]);
    const start = new Date(Math.min(...dates.map((d) => d.getTime())));
    const end = new Date(Math.max(...dates.map((d) => d.getTime())));
    const duration = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);

    return { start, end, duration };
  }, [tasks]);

  // Get current date from progress
  const getDateFromProgress = useCallback(
    (progress: number): string => {
      const timeOffset = (progress / 100) * timelineBounds.duration * 24 * 60 * 60 * 1000;
      const date = new Date(timelineBounds.start.getTime() + timeOffset);
      return date.toISOString().split('T')[0];
    },
    [timelineBounds]
  );

  // Get active tasks at current progress
  const getActiveTasks = useCallback(
    (progress: number): ConstructionTask[] => {
      const currentDateStr = getDateFromProgress(progress);
      const currentDate = new Date(currentDateStr);

      return tasks.filter((task) => {
        const start = new Date(task.startDate);
        const end = new Date(task.endDate);
        return currentDate >= start && currentDate <= end && visibleTasks.has(task.id);
      });
    },
    [tasks, getDateFromProgress, visibleTasks]
  );

  // Animation loop
  useEffect(() => {
    if (isPlaying) {
      const animate = () => {
        setCurrentProgress((prev) => {
          const newProgress = prev + 0.1 * speed;
          if (newProgress >= 100) {
            setIsPlaying(false);
            return 100;
          }

          const newDate = getDateFromProgress(newProgress);
          onDateChange?.(newDate);

          return newProgress;
        });

        animationRef.current = requestAnimationFrame(animate);
      };

      animationRef.current = requestAnimationFrame(animate);
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, speed, getDateFromProgress, onDateChange]);

  const handlePlay = () => setIsPlaying(true);
  const handlePause = () => setIsPlaying(false);
  const handleStop = () => {
    setIsPlaying(false);
    setCurrentProgress(0);
    onDateChange?.(getDateFromProgress(0));
  };

  const handleSliderChange = useCallback(
    (_, value: number | number[]) => {
      const progress = value as number;
      setCurrentProgress(progress);
      onDateChange?.(getDateFromProgress(progress));
    },
    [getDateFromProgress, onDateChange]
  );

  const handleTaskClick = useCallback(
    (task: ConstructionTask) => {
      setSelectedTask(task);
      onTaskSelect?.(task);
    },
    [onTaskSelect]
  );

  const toggleTaskVisibility = useCallback((taskId: string) => {
    setVisibleTasks((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(taskId)) {
        newSet.delete(taskId);
      } else {
        newSet.add(taskId);
      }
      return newSet;
    });
    onTaskVisibilityChange?.(taskId, !visibleTasks.has(taskId));
  }, [onTaskVisibilityChange, visibleTasks]);

  const activeTasks = getActiveTasks(currentProgress);
  const completedTasks = tasks.filter((t) => {
    const end = new Date(t.endDate);
    const current = new Date(getDateFromProgress(currentProgress));
    return end < current;
  });

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" gutterBottom>
          4D Construction Timeline
        </Typography>

        {/* Date Display */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <CalendarIcon color="action" />
          <Typography variant="h5">
            {getDateFromProgress(currentProgress)}
          </Typography>
          <Chip
            label={`Day ${Math.floor((currentProgress / 100) * timelineBounds.duration)}`}
            color="primary"
          />
        </Box>

        {/* Playback Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Tooltip title="Previous">
              <IconButton
                onClick={() => handleSliderChange(null, Math.max(0, currentProgress - 5))}
              >
                <PrevIcon />
              </IconButton>
            </Tooltip>

            {isPlaying ? (
              <Tooltip title="Pause">
                <IconButton onClick={handlePause} color="primary">
                  <PauseIcon />
                </IconButton>
              </Tooltip>
            ) : (
              <Tooltip title="Play">
                <IconButton onClick={handlePlay} color="primary">
                  <PlayIcon />
                </IconButton>
              </Tooltip>
            )}

            <Tooltip title="Stop">
              <IconButton onClick={handleStop}>
                <StopIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="Next">
              <IconButton
                onClick={() => handleSliderChange(null, Math.min(100, currentProgress + 5))}
              >
                <NextIcon />
              </IconButton>
            </Tooltip>
          </Box>

          <FormControl sx={{ minWidth: 100 }} size="small">
            <InputLabel>Speed</InputLabel>
            <Select value={speed} onChange={(e) => setSpeed(e.target.value as number)} label="Speed">
              {PLAYBACK_SPEEDS.map((s) => (
                <MenuItem key={s} value={s}>
                  {s}x
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box sx={{ flexGrow: 1 }} />

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip label={`${activeTasks.length} Active`} color="primary" size="small" />
            <Chip label={`${completedTasks.length} Completed`} color="success" size="small" />
          </Box>
        </Box>

        {/* Timeline Slider */}
        <Box sx={{ mt: 2 }}>
          <Slider
            value={currentProgress}
            onChange={handleSliderChange}
            min={0}
            max={100}
            step={0.1}
            valueLabelDisplay="auto"
            valueLabelFormat={(value) => getDateFromProgress(value)}
          />
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="caption" color="text.secondary">
              {timelineBounds.start.toLocaleDateString()}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {timelineBounds.end.toLocaleDateString()}
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Task List */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">Visible</TableCell>
                <TableCell>Task</TableCell>
                <TableCell>Trade</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tasks.map((task) => {
                const isActive = activeTasks.some((t) => t.id === task.id);
                const isCompleted = completedTasks.some((t) => t.id === task.id);
                const isVisible = visibleTasks.has(task.id);

                return (
                  <TableRow
                    key={task.id}
                    hover
                    selected={isActive}
                    onClick={() => handleTaskClick(task)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={isVisible}
                        onChange={() => toggleTaskVisibility(task.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box
                          sx={{
                            width: 12,
                            height: 12,
                            borderRadius: '50%',
                            backgroundColor: task.color,
                          }}
                        />
                        <Typography variant="body2">{task.name}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip label={task.trade} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>{task.duration} days</TableCell>
                    <TableCell>
                      <LinearProgress
                        variant="determinate"
                        value={task.progress}
                        sx={{ width: 60 }}
                      />
                    </TableCell>
                    <TableCell>
                      {isActive ? (
                        <Chip label="Active" color="primary" size="small" />
                      ) : isCompleted ? (
                        <Chip label="Completed" color="success" size="small" />
                      ) : (
                        <Chip label="Pending" size="small" variant="outlined" />
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* Task Detail Dialog */}
      <Dialog
        open={showTaskDialog}
        onClose={() => setShowTaskDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Task Details</DialogTitle>
        <DialogContent>
          {selectedTask && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
              <TextField
                label="Task Name"
                value={selectedTask.name}
                fullWidth
                disabled
              />
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  label="Start Date"
                  value={selectedTask.startDate}
                  disabled
                  sx={{ flex: 1 }}
                />
                <TextField
                  label="End Date"
                  value={selectedTask.endDate}
                  disabled
                  sx={{ flex: 1 }}
                />
              </Box>
              <TextField
                label="Trade"
                value={selectedTask.trade}
                disabled
              />
              <TextField
                label="Progress"
                type="number"
                value={selectedTask.progress}
                onChange={(e) =>
                  onTaskProgressChange?.(selectedTask.id, parseInt(e.target.value))
                }
                inputProps={{ min: 0, max: 100 }}
              />
              <Typography variant="subtitle2">
                Elements: {selectedTask.elementIds.length}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTaskDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default Timeline4D;
