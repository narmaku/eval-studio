import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from './App';

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(screen.getByText('eval-studio')).toBeInTheDocument();
  });

  it('renders the Dashboard page by default', async () => {
    render(<App />);
    // The page heading "Dashboard" appears as an h1 after lazy load resolves
    const heading = await screen.findByRole('heading', { name: 'Dashboard' });
    expect(heading).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    render(<App />);
    expect(screen.getByText('Evaluate')).toBeInTheDocument();
    expect(screen.getByText('Datasets')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });
});
