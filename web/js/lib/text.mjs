import {validateString, validateNumber} from './type.mjs';

/**
 * Truncate string length by characters.
 *
 * @param {string} text String to format.
 * @param {number} limit Maximum number of characters in resulting string.
 * @param {string} ending Ending to use if string is trucated.
 *
 * @returns {string} Formatted string.
 */
export function limitChars(text, limit = 50, ending = '...') {
  validateString(text);
  validateNumber(limit);
  validateString(ending);

  // Check if string is already below limit
  if (text.length <= limit) {
    return text;
  }

  // Limit string length by characters
  return text.substring(0, limit - ending.length) + ending;
}

/**
 * Truncate string length by words.
 *
 * @param {string} text String to format.
 * @param {number} limit Maximum number of words in resulting string.
 * @param {string} ending Ending to use if string is trucated.
 *
 * @returns {string} Formatted string.
 */
export function limitWords(text, limit = 10, ending = '...') {
  validateString(text);
  validateNumber(limit);
  validateString(ending);

  // Limit string length by words
  return text.split(' ').splice(0, limit).join(' ') + ending;
}
