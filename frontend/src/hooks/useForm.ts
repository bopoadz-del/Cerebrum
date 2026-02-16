import { useState, useCallback, FormEvent } from 'react';
import { z, ZodSchema, ZodError } from 'zod';

interface UseFormOptions<T> {
  initialValues: T;
  validationSchema?: ZodSchema<T>;
  onSubmit: (values: T) => void | Promise<void>;
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
}

interface FormState<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  isValid: boolean;
}

interface UseFormReturn<T> {
  values: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  isValid: boolean;
  handleChange: (name: keyof T, value: unknown) => void;
  handleBlur: (name: keyof T) => void;
  handleSubmit: (e: FormEvent) => Promise<void>;
  setFieldValue: (name: keyof T, value: unknown) => void;
  setFieldError: (name: keyof T, error: string) => void;
  setValues: (values: Partial<T>) => void;
  resetForm: () => void;
  validateField: (name: keyof T) => boolean;
  validateForm: () => boolean;
}

export const useForm = <T extends Record<string, unknown>>(
  options: UseFormOptions<T>
): UseFormReturn<T> => {
  const {
    initialValues,
    validationSchema,
    onSubmit,
    validateOnChange = false,
    validateOnBlur = true,
  } = options;

  const [state, setState] = useState<FormState<T>>({
    values: initialValues,
    errors: {},
    touched: {},
    isSubmitting: false,
    isValid: true,
  });

  // Validate a single field
  const validateField = useCallback(
    (name: keyof T): boolean => {
      if (!validationSchema) return true;

      try {
        // Create a partial schema for single field validation
        const fieldSchema = z.object({
          [name]: (validationSchema as z.ZodObject<Record<keyof T, z.ZodType<unknown>>>).shape[name],
        });

        fieldSchema.parse({ [name]: state.values[name] });

        setState((prev) => ({
          ...prev,
          errors: { ...prev.errors, [name]: undefined },
        }));

        return true;
      } catch (error) {
        if (error instanceof ZodError) {
          const fieldError = error.errors[0]?.message;
          setState((prev) => ({
            ...prev,
            errors: { ...prev.errors, [name]: fieldError },
          }));
        }
        return false;
      }
    },
    [validationSchema, state.values]
  );

  // Validate entire form
  const validateForm = useCallback((): boolean => {
    if (!validationSchema) return true;

    try {
      validationSchema.parse(state.values);
      setState((prev) => ({ ...prev, errors: {}, isValid: true }));
      return true;
    } catch (error) {
      if (error instanceof ZodError) {
        const errors: Partial<Record<keyof T, string>> = {};
        error.errors.forEach((err) => {
          const path = err.path[0] as keyof T;
          if (!errors[path]) {
            errors[path] = err.message;
          }
        });
        setState((prev) => ({ ...prev, errors, isValid: false }));
      }
      return false;
    }
  }, [validationSchema, state.values]);

  // Handle field change
  const handleChange = useCallback(
    (name: keyof T, value: unknown) => {
      setState((prev) => ({
        ...prev,
        values: { ...prev.values, [name]: value },
      }));

      if (validateOnChange) {
        validateField(name);
      }
    },
    [validateOnChange, validateField]
  );

  // Handle field blur
  const handleBlur = useCallback(
    (name: keyof T) => {
      setState((prev) => ({
        ...prev,
        touched: { ...prev.touched, [name]: true },
      }));

      if (validateOnBlur) {
        validateField(name);
      }
    },
    [validateOnBlur, validateField]
  );

  // Set field value programmatically
  const setFieldValue = useCallback((name: keyof T, value: unknown) => {
    setState((prev) => ({
      ...prev,
      values: { ...prev.values, [name]: value },
    }));
  }, []);

  // Set field error programmatically
  const setFieldError = useCallback((name: keyof T, error: string) => {
    setState((prev) => ({
      ...prev,
      errors: { ...prev.errors, [name]: error },
    }));
  }, []);

  // Set multiple values
  const setValues = useCallback((values: Partial<T>) => {
    setState((prev) => ({
      ...prev,
      values: { ...prev.values, ...values },
    }));
  }, []);

  // Reset form to initial values
  const resetForm = useCallback(() => {
    setState({
      values: initialValues,
      errors: {},
      touched: {},
      isSubmitting: false,
      isValid: true,
    });
  }, [initialValues]);

  // Handle form submission
  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();

      // Mark all fields as touched
      const allTouched = Object.keys(state.values).reduce(
        (acc, key) => ({ ...acc, [key]: true }),
        {}
      );

      setState((prev) => ({ ...prev, touched: allTouched }));

      // Validate form
      const isValid = validateForm();
      if (!isValid) return;

      setState((prev) => ({ ...prev, isSubmitting: true }));

      try {
        await onSubmit(state.values);
      } finally {
        setState((prev) => ({ ...prev, isSubmitting: false }));
      }
    },
    [state.values, validateForm, onSubmit]
  );

  return {
    values: state.values,
    errors: state.errors,
    touched: state.touched,
    isSubmitting: state.isSubmitting,
    isValid: state.isValid,
    handleChange,
    handleBlur,
    handleSubmit,
    setFieldValue,
    setFieldError,
    setValues,
    resetForm,
    validateField,
    validateForm,
  };
};

// Helper for creating validation schemas
export const createValidationSchema = <T extends Record<string, unknown>>(
  shape: Record<keyof T, z.ZodType<unknown>>
): ZodSchema<T> => {
  return z.object(shape) as ZodSchema<T>;
};

// Common validation schemas
export const commonSchemas = {
  email: z.string().email('Invalid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  requiredString: z.string().min(1, 'This field is required'),
  url: z.string().url('Invalid URL'),
  phone: z
    .string()
    .regex(
      /^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$/,
      'Invalid phone number'
    ),
};

export default useForm;
