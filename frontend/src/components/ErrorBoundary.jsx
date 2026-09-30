import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="glass-card error-boundary-card" role="alert">
          <div className="error-boundary-header">
            <span className="error-icon" aria-hidden="true">⚠️</span>
            <h2 className="card-title">Something unexpected happened</h2>
          </div>
          <p className="card-subtitle">
            An isolated component error occurred. The rest of the platform remains safe.
          </p>
          {this.state.error && (
            <div className="error-details-box">
              <code>{this.state.error.toString()}</code>
            </div>
          )}
          <div className="error-actions">
            <button
              type="button"
              className="primary-btn"
              onClick={this.handleReset}
            >
              🔄 Reload View
            </button>
            <button
              type="button"
              className="secondary-btn"
              onClick={() => {
                this.handleReset();
                if (window.location.hash || window.location.search) {
                  window.history.pushState({}, '', window.location.pathname);
                }
                window.location.reload();
              }}
            >
              Restart Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
