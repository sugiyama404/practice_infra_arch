module.exports = {
    testEnvironment: 'jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
    testMatch: ['**/__tests__/**/*.(test|spec).(ts|tsx)'],
    moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
};
