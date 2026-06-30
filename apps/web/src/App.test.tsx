import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';

import { App } from './App';
import '@/i18n/index';

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function Wrapper({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe('App', () => {
  it('renders the ABB Assistant heading', () => {
    render(<App />, { wrapper: Wrapper });
    expect(screen.getByText('ABB Assistant')).toBeInTheDocument();
  });
});
