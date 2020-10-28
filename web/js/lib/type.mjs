/**
 * Checks if `value` is the type `Object` excluding `Function` and `null`
 *
 * @param {*} value The value to check.
 * @returns {boolean} Returns `true` if `value` is an object, otherwise `false`.
 */
export function isObject(value) {
  return (Object.prototype.toString.call(value) === '[object Object]');
}

/**
 * Checks if `value` is the type `string`
 *
 * @param {*} value The value to check.
 * @returns {boolean} Returns `true` if `value` is a string, otherwise `false`.
 */
export function isString(value) {
  return (typeof value === 'string');
}

/**
 * Checks if `value` is the type `number`
 *
 * @param {*} value The value to check.
 * @returns {boolean} Returns `true` if `value` is a number, otherwise `false`.
 */
export function isNumber(value) {
  return (typeof value === 'number');
}

/**
 * Validate parameter is of type object.
 *
 * @param {string} value Variable to validate.
 * @throws Error if not an object.
 */
export function validateObject(value) {
  if (!isObject(value)) {
    throw new TypeError('Parameter "value" must be of type object.');
  }
}

/**
 * Validate parameter is of type string.
 *
 * @param {string} value Variable to validate.
 * @throws Error if not an string.
 */
export function validateString(value) {
  if (!isString(value)) {
    throw new TypeError('Parameter "value" must be of type string.');
  }
}

/**
 * Validate parameter is of type number.
 *
 * @param {number} value Variable to validate.
 * @throws Error if not an number.
 */
export function validateNumber(value) {
  if (!isNumber(value)) {
    throw new TypeError('Parameter "value" must be of type number.');
  }
}
