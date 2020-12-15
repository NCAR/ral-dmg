#!/bin/sh
# 0 Success.  The product-queue was opened and the write-count is zero.
# 1 A system-error occurred.
# 2 The product-queue doesn't have a write-count.  If you know that no process has the product-queue open for
#   writing, then you can use the -F option to add write-count capability to the product-queue.
# 3 The product-queue was opened but the write-count is positive.
# 4 The product-queue could not be opened because it is internally inconsistent.  It will have to be deleted and
#   recreated.
#
# man pqcheck (has a typo in it)
# The product-queue exists.  Test for corruption.

if pqcheck -q "$(regutil /queue/path)"; then
  echo "Using existing queue."
else
  case $? in
    1)  echo "Aborting..." ;;
    2)  echo "Adding write-count capability to product-queue"
        if ! pqcheck -F -q $LDMHOME/data/ldm.pq; then
           echo "Aborting..."
        fi
        ;;
    3)  echo "Product-queue incorrectly closed.  Checking..."
        if pqcat -s -l /dev/null; then
          echo "Product-queue appears OK.  Clearing write-count."
          if ! pqcheck -F -q $LDMHOME/data/ldm.pq; then
          echo "Aborting..."
          fi
        else
          echo "Product-queue appears corrupt.  Recreating..."
          /bin/mv -f $LDMHOME/data/ldm.pq $LDMHOME/data/ldm.pq.save
          /bin/su - ldm -c "$LDMBIN/ldmadmin delqueue"
          /bin/su - ldm -c "$LDMBIN/ldmadmin mkqueue"
        fi
        ;;
    4)  echo "Product-queue is corrupt.  Recreating..."
        /bin/mv -f $LDMHOME/data/ldm.pq $LDMHOME/data/ldm.pq.save
        /bin/su - ldm -c "$LDMBIN/ldmadmin delqueue"
        /bin/su - ldm -c "$LDMBIN/ldmadmin mkqueue"
        ;;
  esac
fi
