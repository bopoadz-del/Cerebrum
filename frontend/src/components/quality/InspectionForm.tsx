import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  RadioGroup,
  FormControlLabel,
  Radio,
  Checkbox,
  Grid,
  Divider,
  Alert,
  Chip
} from '@mui/material';
import { PhotoCamera, Save, Send } from '@mui/icons-material';

interface InspectionItem {
  id: string;
  description: string;
  category: string;
  required: boolean;
  response_type: string;
}

interface InspectionFormProps {
  inspectionId: string;
  title: string;
  items: InspectionItem[];
  onSubmit: (responses: any[]) => void;
}

export const InspectionForm: React.FC<InspectionFormProps> = ({
  inspectionId,
  title,
  items,
  onSubmit
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [responses, setResponses] = useState<{ [key: string]: any }>({});
  const [notes, setNotes] = useState('');
  const [photos, setPhotos] = useState<string[]>([]);

  const handleResponse = (itemId: string, value: any) => {
    setResponses(prev => ({
      ...prev,
      [itemId]: value
    }));
  };

  const handleNext = () => {
    setActiveStep(prev => prev + 1);
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  const handleSubmit = () => {
    const formattedResponses = Object.entries(responses).map(([itemId, value]) => ({
      item_id: itemId,
      status: value,
      notes: notes,
      photos: photos
    }));
    onSubmit(formattedResponses);
  };

  const renderResponseInput = (item: InspectionItem) => {
    const value = responses[item.id];

    if (item.response_type === 'pass_fail') {
      return (
        <RadioGroup
          value={value || ''}
          onChange={(e) => handleResponse(item.id, e.target.value)}
        >
          <FormControlLabel
            value="pass"
            control={<Radio />}
            label={<Chip label="Pass" color="success" size="small" />}
          />
          <FormControlLabel
            value="fail"
            control={<Radio />}
            label={<Chip label="Fail" color="error" size="small" />}
          />
          <FormControlLabel
            value="na"
            control={<Radio />}
            label={<Chip label="N/A" size="small" />}
          />
        </RadioGroup>
      );
    }

    if (item.response_type === 'numeric') {
      return (
        <TextField
          type="number"
          value={value || ''}
          onChange={(e) => handleResponse(item.id, e.target.value)}
          variant="outlined"
          size="small"
          fullWidth
        />
      );
    }

    return (
      <TextField
        value={value || ''}
        onChange={(e) => handleResponse(item.id, e.target.value)}
        variant="outlined"
        size="small"
        fullWidth
        multiline
        rows={2}
      />
    );
  };

  const steps = ['Inspection Items', 'Photos', 'Review & Submit'];

  return (
    <Card>
      <CardContent>
        <Typography variant="h5" gutterBottom>
          {title}
        </Typography>
        <Typography variant="subtitle2" color="textSecondary" gutterBottom>
          Inspection ID: {inspectionId}
        </Typography>

        <Stepper activeStep={activeStep} sx={{ my: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {activeStep === 0 && (
          <Box>
            {items.map((item, index) => (
              <Box key={item.id} sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  {index + 1}. {item.description}
                  {item.required && (
                    <Typography component="span" color="error">
                      {' '}*
                    </Typography>
                  )}
                </Typography>
                <Typography variant="caption" color="textSecondary" display="block" gutterBottom>
                  Category: {item.category}
                </Typography>
                {renderResponseInput(item)}
                <TextField
                  placeholder="Add notes..."
                  variant="outlined"
                  size="small"
                  fullWidth
                  sx={{ mt: 1 }}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
                <Divider sx={{ mt: 2 }} />
              </Box>
            ))}
          </Box>
        )}

        {activeStep === 1 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Attach Photos
            </Typography>
            <Button
              variant="outlined"
              component="label"
              startIcon={<PhotoCamera />}
            >
              Upload Photos
              <input
                type="file"
                hidden
                multiple
                accept="image/*"
                onChange={(e) => {
                  // Handle file upload
                }}
              />
            </Button>
            <Grid container spacing={2} sx={{ mt: 2 }}>
              {photos.map((photo, index) => (
                <Grid item key={index}>
                  <Box
                    component="img"
                    src={photo}
                    alt={`Photo ${index + 1}`}
                    sx={{ width: 150, height: 150, objectFit: 'cover' }}
                  />
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {activeStep === 2 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Review & Submit
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              Please review your responses before submitting.
            </Alert>
            <Typography variant="subtitle2" gutterBottom>
              Completion: {Object.keys(responses).length} / {items.length} items
            </Typography>
            <Box sx={{ mt: 2 }}>
              {items.map((item) => (
                <Box key={item.id} sx={{ mb: 1 }}>
                  <Typography variant="body2">
                    {item.description}:{' '}
                    <Chip
                      size="small"
                      label={responses[item.id] || 'Not answered'}
                      color={
                        responses[item.id] === 'pass'
                          ? 'success'
                          : responses[item.id] === 'fail'
                          ? 'error'
                          : 'default'
                      }
                    />
                  </Typography>
                </Box>
              ))}
            </Box>
          </Box>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
          <Button
            disabled={activeStep === 0}
            onClick={handleBack}
          >
            Back
          </Button>
          <Box>
            {activeStep === steps.length - 1 ? (
              <Button
                variant="contained"
                color="primary"
                onClick={handleSubmit}
                startIcon={<Send />}
              >
                Submit Inspection
              </Button>
            ) : (
              <Button
                variant="contained"
                onClick={handleNext}
              >
                Next
              </Button>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export default InspectionForm;
