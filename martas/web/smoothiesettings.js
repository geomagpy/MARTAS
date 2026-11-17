// Customize settings for SmoothieChart (Dark Mode)

let currentYPadding = 0;

function myYRangeFunction(range) {
    if (range.min === range.max) {
        return { min: range.min - 1, max: range.max + 1 };
    }
    return {
        min: range.min - currentYPadding,
        max: range.max + currentYPadding
    };
}

const streamtosettings = {
    Delay: 500
};

const smoothiesettings = {
    yRangeFunction: myYRangeFunction,
    millisPerPixel: 200,
    interpolation: 'bezier',
    scaleSmoothing: 0.25,
    grid: {
        fillStyle: '#11141c',
        strokeStyle: 'rgba(255, 255, 255, 0.07)',
        sharpLines: true,
        millisPerLine: 10000,
        verticalSections: 4,
        borderVisible: false
    },
    labels: {
        fillStyle: '#8b949e',
        fontSize: 11,
        precision: 2
    },
    timestampFormatter: SmoothieChart.timeFormatter
};

// Farbpalette für unterschiedliche Kanäle eines Sensors
const signalColors = [
    '#38bdf8', // Hellblau
    '#fbbf24', // Gelb/Gold
    '#34d399', // Smaragdgrün
    '#f472b6', // Pink
    '#a78bfa', // Violett
    '#fb923c', // Orange
    '#2dd4bf', // Türkis
    '#f87171'  // Koralle
];

function getTimeSeriesSettings(index) {
    const color = signalColors[index % signalColors.length];
    return {
        lineWidth: 2,
        strokeStyle: color,
        fillStyle: color + '1A' // ~10% Transparenz unter der Linie
    };
}