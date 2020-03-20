function [Aang, lang, uang, iang]  = makeAang(baseMVA, branch, nb, mpopt)
%MAKEAANG  Construct constraints for branch angle difference limits.
%   [AANG, LANG, UANG, IANG]  = MAKEAANG(BASEMVA, BRANCH, NB, MPOPT)
%
%   Constructs the parameters for the following linear constraint limiting
%   the voltage angle differences across branches, where Va is the vector
%   of bus voltage angles. NB is the number of buses.
%
%       LANG <= AANG * Va <= UANG
%
%   IANG is the vector of indices of branches with angle difference limits.
%   The limits are given in the ANGMIN and ANGMAX columns of the branch
%   matrix. Voltage angle differences are taken to be unbounded below if
%   ANGMIN < -360 and unbounded above if ANGMAX > 360. If both ANGMIN and
%   ANGMAX are zero, the angle difference is assumed to be unconstrained.
%
%   Example:
%       [Aang, lang, uang, iang]  = makeAang(baseMVA, branch, nb, mpopt);

%   MATPOWER
%   Copyright (c) 1996-2015 by Power System Engineering Research Center (PSERC)
%   by Ray Zimmerman, PSERC Cornell
%   and Carlos E. Murillo-Sanchez, PSERC Cornell & Universidad Autonoma de Manizales
%
%   $Id: makeAang.m 2644 2015-03-11 19:34:22Z ray $
%
%   This file is part of MATPOWER.
%   Covered by the 3-clause BSD License (see LICENSE file for details).
%   See http://www.pserc.cornell.edu/matpower/ for more info.

%% define named indices into data matrices
[F_BUS, T_BUS, BR_R, BR_X, BR_B, RATE_A, RATE_B, RATE_C, ...
    TAP, SHIFT, BR_STATUS, PF, QF, PT, QT, MU_SF, MU_ST, ...
    ANGMIN, ANGMAX, MU_ANGMIN, MU_ANGMAX] = idx_brch;

if mpopt.opf.ignore_angle_lim
  Aang  = sparse(0, nb);
  lang  = [];
  uang  = [];
  iang  = [];
else
  iang = find((branch(:, ANGMIN) & branch(:, ANGMIN) > -360) | ...
              (branch(:, ANGMAX) & branch(:, ANGMAX) < 360));
  nang = length(iang);

  if nang > 0
    ii = [(1:nang)'; (1:nang)'];
    jj = [branch(iang, F_BUS); branch(iang, T_BUS)];
    Aang = sparse(ii, jj, [ones(nang, 1); -ones(nang, 1)], nang, nb);
    lang = branch(iang, ANGMIN) * pi/180;
    uang = branch(iang, ANGMAX) * pi/180;
  else
    Aang = sparse(0, nb);
    lang =[];
    uang =[];
  end
end
