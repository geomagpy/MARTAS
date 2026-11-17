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

// Color palette for distinct sensor channels
const signalColors = [
    '#38bdf8', // Sky Blue
    '#fbbf24', // Amber
    '#34d399', // Emerald
    '#f472b6', // Pink
    '#a78bfa', // Violet
    '#fb923c', // Orange
    '#2dd4bf', // Teal
    '#f87171'  // Coral
];

function getTimeSeriesSettings(index) {
    const color = signalColors[index % signalColors.length];
    return {
        lineWidth: 2,
        strokeStyle: color,
        fillStyle: color + '1A' // ~10% opacity fill beneath line
    };
}