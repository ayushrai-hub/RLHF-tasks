// Decoy Four
// Colors and formats CLI output logs for human reading.

function colorizeText(text, color) {
  const reset = "\x1b[0m";
  let ansiColor = reset;
  switch (color.toLowerCase()) {
    case 'red': ansiColor = "\x1b[31m"; break;
    case 'green': ansiColor = "\x1b[32m"; break;
    case 'yellow': ansiColor = "\x1b[33m"; break;
    case 'blue': ansiColor = "\x1b[34m"; break;
  }
  return `${ansiColor}${text}${reset}`;
}

module.exports = { colorizeText };
