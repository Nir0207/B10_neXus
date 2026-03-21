import React from 'react';
import '@testing-library/jest-dom';
import { render, screen, fireEvent } from '@testing-library/react';
import OrganNavigator from '@/components/OrganNavigator';

describe('OrganNavigator', () => {
  it('renders standard organs', () => {
    const mockOnSelect = jest.fn();
    render(<OrganNavigator selectedOrgan="liver" onSelectOrgan={mockOnSelect} />);
    
    expect(screen.getByText('Organ Atlas')).toBeTruthy();
    expect(screen.getByText('Liver')).toBeTruthy();
    expect(screen.getByText('Heart')).toBeTruthy();
    expect(screen.getByText('Lung')).toBeTruthy();
    expect(screen.getByText('Kidney')).toBeTruthy();
    expect(screen.getByText('Brain')).toBeTruthy();
  });

  it('calls onSelectOrgan when clicked', () => {
    const mockOnSelect = jest.fn();
    render(<OrganNavigator selectedOrgan="liver" onSelectOrgan={mockOnSelect} />);
    
    const heartBtn = screen.getByText('Heart');
    fireEvent.click(heartBtn);
    expect(mockOnSelect).toHaveBeenCalledWith('heart');
  });
});
