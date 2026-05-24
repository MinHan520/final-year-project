import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listScans, deleteScan } from '../api/client';
import type { ScanRow } from '../api/types';

export function useScansList() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['scans'],
    queryFn: listScans,
    staleTime: 2000,
    refetchOnWindowFocus: true,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteScan,
    onMutate: async (scanId) => {
      await queryClient.cancelQueries({ queryKey: ['scans'] });
      const previousScans = queryClient.getQueryData<ScanRow[]>(['scans']);
      queryClient.setQueryData<ScanRow[]>(['scans'], (old) => 
        old?.filter(scan => scan.scan_id !== scanId)
      );
      return { previousScans };
    },
    onError: (_err, _scanId, context) => {
      queryClient.setQueryData(['scans'], context?.previousScans);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] });
    },
  });

  return {
    scans: query.data || [],
    isLoading: query.isLoading,
    error: query.error,
    deleteScan: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
  };
}
