import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getUserAreasApi, createAreaApi, deleteAreaApi } from '../api/auth';
import ErrorBox from '../components/ErrorBox';
import CreateAreaForm from '../components/CreateAreaForm';
import AreaCard from '../components/AreaCard';
import './DashboardPage.css';

export default function DashboardPage() {
  const { user, token, loading: authLoading } = useAuth();
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [creatingArea, setCreatingArea] = useState(false);

  useEffect(() => {
    const fetchAreas = async () => {
      if (!user) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const areasData = await getUserAreasApi(token, user.user_id);
        setAreas(areasData || []);
      } catch (err) {
        setError(err.message || 'Failed to load areas');
      } finally {
        setLoading(false);
      }
    };

    fetchAreas();
  }, [user, token]);

  const handleCreateArea = async (coordinates) => {
    try {
      setCreatingArea(true);
      setError(null);
      
      const result = await createAreaApi(token, user.user_id, {
        type: 'Polygon',
        coordinates: [coordinates],
      });
      
      // Refresh areas
      const areasData = await getUserAreasApi(token, user.user_id);
      setAreas(areasData);
      
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
      // Refresh areas after deletion
      const areasData = await getUserAreasApi(token, user.user_id);
      setAreas(areasData);
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
        {areas.length === 0 ? (
          <p className="no-areas">No areas assigned yet.</p>
        ) : (
          <div className="areas-list">
            {areas.map((area) => (
              <AreaCard
                key={area.id || area.user_id}
                area={area}
                onDelete={user?.role === 'admin' ? () => handleDeleteArea(area.user_id) : undefined}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}