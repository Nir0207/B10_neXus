module.exports = {
  useQuery: jest.fn(),
  QueryClient: jest.fn().mockImplementation(() => ({
    clear: jest.fn()
  })),
  QueryClientProvider: ({ children }) => children
};
