import { render, screen } from '@testing-library/react';

import { App } from './App';

describe('App', () => {
  it('renders the product name', () => {
    // Arrange
    render(<App />);

    // Act
    const heading = screen.getByRole('heading', { name: 'ABB Assistant' });

    // Assert
    expect(heading).toBeInTheDocument();
  });
});
