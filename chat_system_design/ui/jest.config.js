module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testMatch: ['**/?(*.)+(test|spec).[tj]s?(x)'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
};
