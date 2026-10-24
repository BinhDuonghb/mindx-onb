/**
 * Validator for positive integers in API parameters.
 * Ensures topK and limit parameters are valid positive integers.
 */

export interface ValidationResult {
  isValid: boolean;
  error?: string;
  value?: number;
}

export class PositiveIntegerValidator {
  /**
   * Check if value is a positive integer (> 0).
   */
  static isValid(value: unknown): value is number {
    return typeof value === 'number' && Number.isInteger(value) && value > 0;
  }

  /**
   * Validate positive integer and return result.
   */
  static validate(value: unknown, paramName: string): ValidationResult {
    // Check type
    if (typeof value !== 'number') {
      return {
        isValid: false,
        error: `${paramName} must be a number, got ${typeof value}`
      };
    }

    // Check integer
    if (!Number.isInteger(value)) {
      return {
        isValid: false,
        error: `${paramName} must be an integer, got ${value}`
      };
    }

    // Check positive
    if (value <= 0) {
      return {
        isValid: false,
        error: `${paramName} must be a positive integer (> 0), got ${value}`
      };
    }

    return {
      isValid: true,
      value
    };
  }

  /**
   * Validate and return value with default fallback.
   * Used for API parameters where we want to apply defaults.
   */
  static validateWithDefault(
    value: unknown,
    paramName: string,
    defaultValue: number
  ): { isValid: boolean; value: number; error?: string } {
    // If it's not a number or not valid, use default
    if (typeof value !== 'number' || !Number.isInteger(value) || value <= 0) {
      return {
        isValid: true, // Still valid (using default)
        value: defaultValue
      };
    }

    return {
      isValid: true,
      value
    };
  }
}
