import React from 'react';
import '@testing-library/jest-dom';
import { render, screen, fireEvent } from '@testing-library/react';
import BioChat from '@/components/BioChat';

describe('BioChat', () => {
  it('renders chat interface correctly', () => {
    render(<BioChat />);
    expect(screen.getByText('Bio-Chat Assistant')).toBeTruthy();
    expect(screen.getByPlaceholderText('Ask Bio-Chat...')).toBeTruthy();
  });

  it('clears input upon form submission', () => {
    render(<BioChat />);
    const input = screen.getByPlaceholderText('Ask Bio-Chat...') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'What is CYP3A4?' } });
    expect(input.value).toBe('What is CYP3A4?');
    
    // Find the form button to submit
    const button = screen.getByRole('button', { name: /send/i });
    fireEvent.click(button);
    
    // Expect input to be cleared
    expect(input.value).toBe('');
  });
});
