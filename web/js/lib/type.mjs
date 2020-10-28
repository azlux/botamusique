/**
 * Checks if `value` is the type `Object` excluding `Function` and `null`
 *
 * @param {*} value The value to check.
 * @returns {boolean} Returns `true` if `value` is an object, else `false`.
 */
export function isObject(value) {
  return (Object.prototype.toString.call(value) === '[object Object]');
}

/**
 * Validate parameter is of type string.
 *
 * @param {string} text Variable to validate.
 */
export function validateString(text) {
  if (typeof text !== 'string') {
    throw new TypeError('Parameter "text" must be of type string.');
  }
}

/**
 * Validate parameter is of type number.
 *
 * @param {number} num Variable to validate.
 */
export function validateNumber(num) {
  if (typeof num !== 'number') {
    throw new TypeError('Parameter "num" must be of type number.');
  }
}
