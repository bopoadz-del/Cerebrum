import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Slider,
  Button,
  IconButton,
  Tooltip,
  LinearProgress,
  Chip,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  FastForward as FastForwardIcon,
  FastRewind as FastRewindIcon,
  CalendarToday as CalendarIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';

interface ConstructionTask {
  id: string;
  name: string;
  wbsCode: string;
  taskType: string;
  startDate: string;
  endDate: string;
  durationDays: number;
  status: 'not_started' | 'in_progress' | 'completed' | 'delayed';
  percentComplete: number;
  linkedElements: string[];
  criticalPath: boolean;
}

interface TimelinePoint {
  date: string;
  activeTasks: number;
  completedElements: number;
  progress: number;
}

const Schedule4D: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<ConstructionTask[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [projectStart, setProjectStart] = useState<Date>(new Date());
  const [projectEnd, setProjectEnd] = useState<Date>(new Date());
  const [overallProgress, setOverallProgress] = useState(0);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    // Simulate loading schedule data
    const timer = setTimeout(() => {
      loadMockData();
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (isPlaying) {
      startAnimation();
    } else {
      stopAnimation();
    }
    return () => stopAnimation();
  }, [isPlaying, playbackSpeed]);

  const loadMockData = () => {
    const start = new Date('2024-01-01');
    const end = new Date('2024-12-31');
    
    setProjectStart(start);
    setProjectEnd(end);
    setCurrentDate(start);

    const mockTasks: ConstructionTask[] = [
      {
        id: 'task-001',
        name: 'Foundation Excavation',
        wbsCode: '1.1',
        taskType: 'foundation',
        startDate: '2024-01-01',
        endDate: '2024-01-15',
        durationDays: 14,
        status: 'completed',
        percentComplete: 100,
        linkedElements: ['elem-001', 'elem-002'],
        criticalPath: true,
      },
      {
        id: 'task-002',
        name: 'Foundation Concrete',
        wbsCode: '1.2',
        taskType: 'foundation',
        startDate: '2024-01-15',
        endDate: '2024-02-01',
        durationDays: 17,
        status: 'completed',
        percentComplete: 100,
        linkedElements: ['elem-003', 'elem-004'],
        criticalPath: true,
      },
      {
        id: 'task-003',
        name: 'Structural Steel',
        wbsCode: '2.1',
        taskType: 'structure',
        startDate: '2024-02-01',
        endDate: '2024-04-15',
        durationDays: 73,
        status: 'in_progress',
        percentComplete: 65,
        linkedElements: ['elem-005', 'elem-006', 'elem-007'],
        criticalPath: true,
      },
      {
        id: 'task-004',
        name: 'MEP Rough-in',
        wbsCode: '3.1',
        taskType: 'mep_rough',
        startDate: '2024-04-15',
        endDate: '2024-06-30',
        durationDays: 76,
        status: 'not_started',
        percentComplete: 0,
        linkedElements: ['elem-008', 'elem-009'],
        criticalPath: false,
      },
      {
        id: 'task-005',
        name: 'Interior Finishes',
        wbsCode: '4.1',
        taskType: 'interior',
        startDate: '2024-07-01',
        endDate: '2024-10-15',
        durationDays: 106,
        status: 'not_started',
        percentComplete: 0,
        linkedElements: ['elem-010', 'elem-011'],
        criticalPath: false,
      },
    ];

    setTasks(mockTasks);

    // Generate timeline
    const timelineData: TimelinePoint[] = [];
    let current = new Date(start);
    while (current <= end) {
      const activeTasks = mockTasks.filter(
        t => new Date(t.startDate) <= current && new Date(t.endDate) >= current
      ).length;
      
      const completedElements = mockTasks
        .filter(t => new Date(t.endDate) < current)
        .reduce((sum, t) => sum + t.linkedElements.length, 0);

      const progress = Math.min(
        100,
        ((current.getTime() - start.getTime()) / (end.getTime() - start.getTime())) * 100
      );

      timelineData.push({
        date: current.toISOString().split('T')[0],
        activeTasks,
        completedElements,
        progress: Math.round(progress),
      });

      current.setDate(current.getDate() + 7); // Weekly points
    }

    setTimeline(timelineData);
    setOverallProgress(35);
  };

  const startAnimation = () => {
    const animate = () => {
      setCurrentDate(prev => {
        const next = new Date(prev);
        next.setDate(next.getDate() + playbackSpeed);
        
        if (next > projectEnd) {
          setIsPlaying(false);
          return projectEnd;
        }
        
        return next;
      });
      
      animationRef.current = requestAnimationFrame(animate);
    };
    
    animationRef.current = requestAnimationFrame(animate);
  };

  const stopAnimation = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
  };

  const handlePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleStop = () => {
    setIsPlaying(false);
    setCurrentDate(projectStart);
  };

  const handleSliderChange = (_: Event, value: number | number[]) => {
    const daysFromStart = value as number;
    const newDate = new Date(projectStart);
    newDate.setDate(newDate.getDate() + daysFromStart);
    setCurrentDate(newDate);
  };

  const getDaysFromStart = () => {
    return Math.floor(
      (currentDate.getTime() - projectStart.getTime()) / (1000 * 60 * 60 * 24)
    );
  };

  const getTotalDays = () => {
    return Math.floor(
      (projectEnd.getTime() - projectStart.getTime()) / (1000 * 60 * 60 * 24)
    );
  };

  const getActiveTasksForDate = (date: Date) => {
    return tasks.filter(task => {
      const start = new Date(task.startDate);
      const end = new Date(task.endDate);
      return date >= start && date <= end;
    });
  };

  const getVisibleElementsForDate = (date: Date) => {
    return tasks
      .filter(task => new Date(task.endDate) <= date)
      .flatMap(task => task.linkedElements);
  };

  const getTaskStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'in_progress':
        return 'info';
      case 'delayed':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2 }}>Loading 4D schedule...</Typography>
      </Box>
    );
  }

  const activeTasks = getActiveTasksForDate(currentDate);
  const visibleElements = getVisibleElementsForDate(currentDate);

  return (
    <Box>
      {/* Timeline Controls */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item>
            <Button
              variant="contained"
              startIcon={isPlaying ? <PauseIcon /> : <PlayIcon />}
              onClick={handlePlay}
            >
              {isPlaying ? 'Pause' : 'Play'}
            </Button>
          </Grid>
          <Grid item>
            <Button
              variant="outlined"
              startIcon={<StopIcon />}
              onClick={handleStop}
            >
              Stop
            </Button>
          </Grid>
          <Grid item xs>
            <Slider
              value={getDaysFromStart()}
              min={0}
              max={getTotalDays()}
              onChange={handleSliderChange}
              valueLabelDisplay="auto"
              valueLabelFormat={value => {
                const date = new Date(projectStart);
                date.setDate(date.getDate() + value);
                return date.toLocaleDateString();
              }}
            />
          </Grid>
          <Grid item>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Speed</InputLabel>
              <Select
                value={playbackSpeed}
                onChange={e => setPlaybackSpeed(Number(e.target.value))}
              >
                <MenuItem value={1}>1x</MenuItem>
                <MenuItem value={5}>5x</MenuItem>
                <MenuItem value={10}>10x</MenuItem>
                <MenuItem value={30}>30x</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>

        {/* Current Date Display */}
        <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
          <CalendarIcon color="primary" />
          <Typography variant="h5">
            {currentDate.toLocaleDateString('en-US', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </Typography>
          <Chip
            label={`${Math.round((getDaysFromStart() / getTotalDays()) * 100)}% complete`}
            color="primary"
          />
        </Box>
      </Paper>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Active Tasks
              </Typography>
              <Typography variant="h4">{activeTasks.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Visible Elements
              </Typography>
              <Typography variant="h4">{visibleElements.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Overall Progress
              </Typography>
              <Typography variant="h4">{overallProgress}%</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Days Remaining
              </Typography>
              <Typography variant="h4">
                {Math.max(0, getTotalDays() - getDaysFromStart())}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Task List */}
      <Paper sx={{ mb: 2 }}>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">
            <TimelineIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Construction Tasks
          </Typography>
        </Box>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>WBS</TableCell>
                <TableCell>Task Name</TableCell>
                <TableCell>Start Date</TableCell>
                <TableCell>End Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Elements</TableCell>
                <TableCell>Critical</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tasks.map(task => {
                const isActive =
                  new Date(task.startDate) <= currentDate &&
                  new Date(task.endDate) >= currentDate;
                
                return (
                  <TableRow
                    key={task.id}
                    sx={{
                      backgroundColor: isActive
                        ? 'rgba(25, 118, 210, 0.08)'
                        : 'inherit',
                    }}
                  >
                    <TableCell>{task.wbsCode}</TableCell>
                    <TableCell>{task.name}</TableCell>
                    <TableCell>
                      {new Date(task.startDate).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {new Date(task.endDate).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={task.status.replace('_', ' ')}
                        color={getTaskStatusColor(task.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Box sx={{ width: 60, mr: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={task.percentComplete}
                          />
                        </Box>
                        <Typography variant="body2">
                          {task.percentComplete}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{task.linkedElements.length}</TableCell>
                    <TableCell>
                      {task.criticalPath && (
                        <Chip label="Critical" color="error" size="small" />
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Timeline Chart Placeholder */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Timeline Visualization
        </Typography>
        <Box
          sx={{
            height: 200,
            backgroundColor: '#f5f5f5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 1,
          }}
        >
          <Typography color="text.secondary">
            Gantt Chart Visualization (Integrate with library like @mui/x-charts or vis-timeline)
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default Schedule4D;
