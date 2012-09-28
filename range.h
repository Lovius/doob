#ifndef DOOB_RANGE_HH
#define DOOB_RANGE_HH

#include <types.h>

namespace doob {

struct range {
	range(tick_t start = 0, tick_t end = 64) :
		start(start),
		end(end)
	{
		
	}
	
	/**
	 * The start tick is included i.e. start <= range
	 */
	tick_t start;
	
	/**
	 * The end tick is excluded range < end
	 */
	tick_t end;
};

} // namespace

#endif
