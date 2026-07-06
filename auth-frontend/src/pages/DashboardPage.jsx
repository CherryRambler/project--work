import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getUserAreasApi, createAreaApi, deleteAreaApi } from '../api/auth';
import ErrorBox from '../components/ErrorBox';
import CreateAreaForm from '../components/CreateAreaForm';
import AreaCard from '../components/AreaCard';
import AreaMap from '../components/AreaMap';
import './DashboardPage.css';

export default function DashboardPage() {
  const { user, token, loading: authLoading } = useAuth();
  const [area, setArea] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [creatingArea, setCreatingArea] = useState(false);

  useEffect(() => {
    const fetchArea = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const areaData = await getUserAreasApi(token, user.user_id);
        setArea(areaData?.has_area ? areaData : null);
      } catch (err) {
        setError(err.message || 'Failed to load areas');
      } finally {
        setLoading(false);
      }
    };

    fetchArea();
  }, [user, token]);

  const handleCreateArea = async (coordinates) => {
    try {
      setCreatingArea(true);
      setError(null);

      await createAreaApi(token, user.user_id, coordinates);

      // Refresh area
      const areaData = await getUserAreasApi(token, user.user_id);
      setArea(areaData?.has_area ? areaData : null);

      setSuccessMessage('Area created successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to create area');
    } finally {
      setCreatingArea(false);
    }
  };

  const handleDeleteArea = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this area?')) return;

    try {
      await deleteAreaApi(token, userId);
      setArea(null);
    } catch (err) {
      setError(err.message || 'Failed to delete area');
    }
  };

  // Show loading indicator
  if (authLoading || loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {successMessage && (
        <div className="success-box" role="alert">
          {successMessage}
        </div>
      )}
      
      {error && <ErrorBox message={error} />}

      <div className="dashboard-header">
        <h2>Welcome, {user?.user_name || 'User'}!</h2>
        <p className="user-role">Role: {user?.role}</p>
      </div>

      {user?.role === 'admin' && (
        <CreateAreaForm onSubmit={handleCreateArea} isLoading={creatingArea} />
      )}

      <div className="areas-section">
        <h3>Your Authorized Areas</h3>
        {!area ? (
          <p className="no-areas">No areas assigned yet.</p>
        ) : (
          <div className="areas-list">
            <AreaCard
              key={area.user_id}
              area={area}
              onDelete={user?.role === 'admin' ? () => handleDeleteArea(area.user_id) : undefined}
            />
            <AreaMap area={area} />
          </div>
        )}
      </div>
    </div>
  );
}