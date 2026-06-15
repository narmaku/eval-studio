import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Stub child components to isolate the Settings page layout
vi.mock('@/components/settings/RubricList', () => ({
  RubricList: () => <div data-testid="rubric-list">Rubric List Content</div>,
}));

vi.mock('@/components/settings/ProviderList', () => ({
  ProviderList: () => <div data-testid="provider-list">Provider List Content</div>,
}));

describe('Settings page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function renderPage() {
    const mod = await import('./Settings');
    const Settings = mod.default;
    return render(<Settings />);
  }

  it('renders page heading', async () => {
    await renderPage();
    expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument();
  });

  it('renders tab triggers', async () => {
    await renderPage();
    expect(screen.getByRole('tab', { name: /rubrics/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /providers/i })).toBeInTheDocument();
  });

  it('shows Rubrics tab content by default', async () => {
    await renderPage();
    expect(screen.getByTestId('rubric-list')).toBeInTheDocument();
  });

  it('switches to Providers tab', async () => {
    const user = userEvent.setup();
    await renderPage();

    await user.click(screen.getByRole('tab', { name: /providers/i }));

    expect(screen.getByTestId('provider-list')).toBeInTheDocument();
  });
});
